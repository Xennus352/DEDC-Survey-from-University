"""Regression coverage for dashboard requests and native builder persistence."""
from datetime import date, datetime, timedelta, timezone
import json
from sqlalchemy import func, select

from app.admin_auth import COOKIE_NAME
from app.portal_auth import csrf_token

from test_portal import PortalFixture
from app.storage.existing import metadata


class DashboardRecoveryTests(PortalFixture):
    persistent_metadata = metadata

    async def admin_request(self, path, method="GET", data=None, csrf=True):
        headers = [(b"x-csrf-token", csrf_token(self.cookies[COOKIE_NAME].value).encode())] if csrf else []
        status, headers, body = await self.request(
            "/api/admin" + path, method, extra_headers=headers,
            raw_body=json.dumps(data).encode() if data is not None else b"",
            content_type="application/json",
        )
        return status, headers, json.loads(body) if body else None

    async def test_dashboard_data_endpoints_return_the_workspace_contract(self):
        await self.login()
        for path, keys in (
            ('/overview', ('forms', 'submissions', 'trend', 'answer_trend', 'completed_by_year')),
            ('/forms?limit=100', ('items', 'total')),
            ('/reports', ('items', 'total', 'statuses')),
            ('/reports/university', ('totals', 'active_years', 'recent_reports')),
            ('/users?limit=100', ('items', 'roles', 'total')),
            ('/audit', ('items', 'total')),
        ):
            status, _, data = await self.admin_request(path)
            self.assertEqual(status, 200, (path, data))
            for key in keys:
                self.assertIn(key, data, path)

    async def test_overview_counts_published_questions_and_native_activity(self):
        await self.login()
        with self.sessions() as db:
            published_year = db.native.execute(
                metadata.tables['year'].insert().values(
                    yearFrom=date(2026, 1, 1), yearTo=date(2026, 12, 31), status=1,
                )
            ).inserted_primary_key[0]
            draft_year = db.native.execute(
                metadata.tables['year'].insert().values(
                    yearFrom=date(2027, 1, 1), yearTo=date(2027, 12, 31), status=0,
                )
            ).inserted_primary_key[0]
            university_id = db.native.execute(metadata.tables['university'].insert().values(
                uniType='CU', uniName='Test University',
            )).inserted_primary_key[0]
            ministry_id = db.native.execute(metadata.tables['ministry'].insert().values(
                ministryName='Test Ministry',
            )).inserted_primary_key[0]
            second_university_id = db.native.execute(metadata.tables['university'].insert().values(
                uniType='TU', uniName='Second University',
            )).inserted_primary_key[0]
            university_questions = [
                db.native.execute(metadata.tables['uniquestion'].insert().values(
                    yID=published_year, uQDetail=f'University question {number}',
                )).inserted_primary_key[0]
                for number in (1, 2)
            ]
            db.native.execute(metadata.tables['uniquestion'].insert().values(
                yID=draft_year, uQDetail='Draft question',
            ))
            ministry_question = db.native.execute(
                metadata.tables['ministryquestion'].insert().values(
                    yID=published_year, mQDetail='Ministry question',
                )
            ).inserted_primary_key[0]
            submitted_at = datetime.now(timezone.utc).replace(
                tzinfo=None, hour=12, minute=0, second=0, microsecond=0,
            ) - timedelta(days=1)
            for question_id in university_questions:
                db.native.execute(metadata.tables['unisurvey'].insert().values(
                    uniId=university_id, uQId=question_id,
                    hasItem=False, submittedAt=submitted_at,
                ))
            db.native.execute(metadata.tables['ministrysurvey'].insert().values(
                ministryId=ministry_id, mQId=ministry_question,
                hasItem=False, submittedAt=submitted_at,
            ))
            db.commit()

        status, _, data = await self.admin_request('/overview')
        self.assertEqual(status, 200)
        self.assertEqual(data['directory_stats'], {
            'university_questions': 2,
            'ministry_questions': 1,
            'universities': 2,
            'ministries': 1,
        })
        chart_years = list(range(datetime.now().year - 3, datetime.now().year + 1))
        self.assertEqual(data['completed_by_year'], {
            'years': chart_years,
            'university': {'series': [
                {'label': 'CU', 'values': [2 if year == submitted_at.year else 0 for year in chart_years]},
                {'label': 'TU', 'values': [0 for _ in chart_years]},
            ]},
            'ministry': {'series': [
                {'label': 'Test Ministry', 'values': [1 if year == submitted_at.year else 0 for year in chart_years]},
            ]},
        })
        self.assertEqual(data['form_status'], {
            'published': 2, 'draft': 1, 'archived': 0,
        })
        self.assertEqual(sum(day['count'] for day in data['trend']), 2)
        self.assertEqual(
            next(day['count'] for day in data['trend'] if day['date'] == submitted_at.date().isoformat()),
            2,
        )
        self.assertEqual(len(data['answer_trend']), 30)
        self.assertEqual(
            next(day for day in data['answer_trend'] if day['date'] == submitted_at.date().isoformat()),
            {'date': submitted_at.date().isoformat(), 'university': 2, 'ministry': 1},
        )

    async def test_completed_answers_group_by_submission_year_and_organization(self):
        await self.login()
        with self.sessions() as db:
            years = [db.native.execute(metadata.tables['year'].insert().values(
                yearFrom=date(year, 1, 1), yearTo=date(year, 12, 31), status=1,
            )).inserted_primary_key[0] for year in (2025, 2026)]
            universities = [db.native.execute(metadata.tables['university'].insert().values(
                uniType=kind, uniName=name,
            )).inserted_primary_key[0] for kind, name in (
                ('CU', 'Computer A'), ('CU', 'Computer B'), ('TU', 'Technical A'),
            )]
            ministries = [db.native.execute(metadata.tables['ministry'].insert().values(
                ministryName=name,
            )).inserted_primary_key[0] for name in ('Ministry A', 'Ministry B')]
            university_questions = [db.native.execute(
                metadata.tables['uniquestion'].insert().values(yID=year_id, uQDetail='Question')
            ).inserted_primary_key[0] for year_id in years]
            ministry_questions = [db.native.execute(
                metadata.tables['ministryquestion'].insert().values(yID=year_id, mQDetail='Question')
            ).inserted_primary_key[0] for year_id in years]
            for uni_id, question_id, submitted_year in (
                (universities[0], university_questions[0], 2025),
                (universities[1], university_questions[0], 2026),
                (universities[2], university_questions[1], 2026),
            ):
                db.native.execute(metadata.tables['unisurvey'].insert().values(
                    uniId=uni_id, uQId=question_id, hasItem=False,
                    submittedAt=datetime(submitted_year, 11, 13, 12, 0),
                ))
            for ministry_id, question_id, submitted_year in (
                (ministries[0], ministry_questions[0], 2025),
                (ministries[1], ministry_questions[1], 2026),
            ):
                db.native.execute(metadata.tables['ministrysurvey'].insert().values(
                    ministryId=ministry_id, mQId=question_id, hasItem=False,
                    submittedAt=datetime(submitted_year, 11, 13, 12, 0),
                ))
            db.commit()

        status, _, data = await self.admin_request('/overview')
        self.assertEqual(status, 200)
        chart_years = data['completed_by_year']['years']
        self.assertTrue({2025, 2026}.issubset(chart_years))
        self.assertEqual(data['completed_by_year'], {
            'years': chart_years,
            'university': {'series': [
                {'label': 'CU', 'values': [1 if year in (2025, 2026) else 0 for year in chart_years]},
                {'label': 'TU', 'values': [1 if year == 2026 else 0 for year in chart_years]},
            ]},
            'ministry': {'series': [
                {'label': 'Ministry A', 'values': [1 if year == 2025 else 0 for year in chart_years]},
                {'label': 'Ministry B', 'values': [1 if year == 2026 else 0 for year in chart_years]},
            ]},
        })

    async def test_university_report_summary_tracks_active_year_progress(self):
        await self.login()
        status, _, created = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'university',
            'start_year': 2027,
            'start_month': 2,
            'end_year': 2027,
            'end_month': 2,
            'status': 1,
            'groups': [
                {'title': 'Infrastructure', 'questions': ['Fiber connection', 'Computer lab']},
            ],
        })
        self.assertEqual(status, 201, created)
        active_year_id = created['year_id']
        question_ids = created['groups'][0]['question_ids']

        with self.sessions() as db:
            university_table = metadata.tables['university']
            survey_table = metadata.tables['unisurvey']
            year_table = metadata.tables['year']
            title_table = metadata.tables['questiontitle']
            question_table = metadata.tables['uniquestion']
            university_ids = {}
            for name in ('Alpha University', 'Beta University', 'Gamma University'):
                result = db.native.execute(
                    university_table.insert().values(
                        uniType='Public university', uniName=name,
                    )
                )
                university_ids[name] = result.inserted_primary_key[0]

            for name, submitted_at, answered_ids in (
                ('Alpha University', datetime(2026, 11, 9, 9, 0), question_ids),
                ('Beta University', datetime(2026, 11, 10, 9, 0), question_ids[:1]),
            ):
                for question_id in answered_ids:
                    db.native.execute(
                        survey_table.insert().values(
                            uniId=university_ids[name],
                            uQId=question_id,
                            hasItem=False,
                            itemCount=0,
                            submittedAt=submitted_at,
                        )
                    )

            inactive_year_id = db.native.execute(
                year_table.insert().values(
                    yearFrom=date(2025, 1, 1),
                    yearTo=date(2025, 1, 1),
                    status=0,
                )
            ).inserted_primary_key[0]
            inactive_title_id = db.native.execute(
                title_table.insert().values(qTDetail='Inactive title')
            ).inserted_primary_key[0]
            inactive_question_id = db.native.execute(
                question_table.insert().values(
                    uQDetail='Inactive question',
                    qTID=inactive_title_id,
                    yID=inactive_year_id,
                )
            ).inserted_primary_key[0]
            db.native.execute(
                survey_table.insert().values(
                    uniId=university_ids['Gamma University'],
                    uQId=inactive_question_id,
                    hasItem=False,
                    itemCount=0,
                    submittedAt=datetime(2026, 11, 11, 9, 0),
                )
            )
            db.commit()

        status, _, summary = await self.admin_request('/reports/university')
        self.assertEqual(status, 200, summary)
        totals = summary['totals']
        self.assertEqual(totals['universities'], 3)
        self.assertEqual(totals['active_years'], 1)
        self.assertEqual(totals['questions'], 2)
        self.assertEqual(totals['reports_expected'], 3)
        self.assertEqual(totals['reports_submitted'], 2)
        self.assertEqual(totals['reports_pending'], 1)
        self.assertEqual(totals['participating_universities'], 2)
        self.assertEqual(totals['answers'], 3)
        self.assertEqual(totals['completion_percent'], 66.7)
        self.assertEqual(totals['answer_coverage_percent'], 50.0)
        self.assertEqual(totals['last_submitted_at'], '2026-11-10T09:00:00')

        self.assertEqual(len(summary['active_years']), 1)
        year = summary['active_years'][0]
        self.assertEqual(year['year_id'], active_year_id)
        self.assertEqual(year['label'], 'February 2027')
        self.assertEqual(year['question_count'], 2)
        self.assertEqual(year['submitted_universities'], 2)
        self.assertEqual(year['pending_universities'], 1)
        self.assertEqual(year['answer_rows'], 3)
        self.assertEqual(year['completion_percent'], 66.7)
        self.assertEqual(year['answer_coverage_percent'], 50.0)
        self.assertEqual(year['status'], 'in_progress')

        recent = summary['recent_reports']
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]['university'], 'Beta University')
        self.assertEqual(recent[0]['status'], 'in_progress')
        self.assertEqual(recent[0]['completion_percent'], 50.0)
        self.assertEqual(recent[1]['university'], 'Alpha University')
        self.assertEqual(recent[1]['status'], 'completed')
        self.assertNotIn(
            'Gamma University', [report['university'] for report in recent],
        )

        status, _, answered = await self.admin_request(
            f'/reports/university/{active_year_id}/universities?state=answered'
        )
        self.assertEqual(status, 200, answered)
        self.assertEqual(answered['state'], 'answered')
        self.assertEqual(answered['question_count'], 2)
        self.assertEqual(answered['total'], 2)
        self.assertEqual(
            [row['university'] for row in answered['universities']],
            ['Alpha University', 'Beta University'],
        )
        alpha, beta = answered['universities']
        self.assertEqual(alpha['answered_questions'], 2)
        self.assertEqual(alpha['status'], 'completed')
        self.assertEqual(alpha['last_submitted_at'], '2026-11-09T09:00:00')
        self.assertEqual(beta['answered_questions'], 1)
        self.assertEqual(beta['completion_percent'], 50.0)
        self.assertEqual(beta['status'], 'in_progress')

        status, _, pending = await self.admin_request(
            f'/reports/university/{active_year_id}/universities?state=pending'
        )
        self.assertEqual(status, 200, pending)
        self.assertEqual(pending['state'], 'pending')
        self.assertEqual(pending['total'], 1)
        self.assertEqual(pending['universities'][0]['university'], 'Gamma University')
        self.assertEqual(pending['universities'][0]['answered_questions'], 0)
        self.assertEqual(pending['universities'][0]['status'], 'not_started')

        status, _, _ = await self.admin_request(
            f'/reports/university/{inactive_year_id}/universities?state=answered'
        )
        self.assertEqual(status, 404)

        status, _, _ = await self.admin_request(
            f'/reports/university/{active_year_id}/universities?state=unknown'
        )
        self.assertEqual(status, 422)

    async def test_builder_year_and_question_survive_new_requests(self):
        await self.login()
        status, _, year = await self.admin_request('/survey/years', 'POST', {
            'year_from': 3, 'year_to': 2026, 'status': 1,
        })
        self.assertEqual(status, 201, year)
        self.assertEqual(year['year_from'], 3)
        _, _, matching = await self.admin_request('/survey/years?search=2026')
        self.assertEqual([row['yID'] for row in matching], [year['yID']])
        _, _, missing = await self.admin_request('/survey/years?search=2030')
        self.assertEqual(missing, [])
        status, _, title = await self.admin_request('/survey/question-titles', 'POST', {
            'qTDetail': 'Digital facilities',
        })
        self.assertEqual(status, 201, title)
        status, _, question = await self.admin_request('/survey/questions/university', 'POST', {
            'yID': year['yID'], 'qTID': title['qTID'], 'uQDetail': 'Computer laboratories',
        })
        self.assertEqual(status, 201, question)
        status, _, groups = await self.admin_request(f"/survey/builder/groups/university/{year['yID']}")
        self.assertEqual(status, 200, groups)
        self.assertEqual(groups['org_type'], 'university')
        self.assertEqual(len(groups['groups']), 1)
        self.assertEqual(groups['groups'][0]['qTDetail'], 'Digital facilities')
        self.assertEqual(
            groups['groups'][0]['questions'][0]['detail'], 'Computer laboratories',
        )
        self.assertEqual(groups['groups'][0]['questions'][0]['id'], question['uQId'])
        status, _, data = await self.admin_request(f"/survey/years/{year['yID']}")
        self.assertEqual(data['year_from'], 3)
        with self.sessions() as db:
            row = db.native.execute(metadata.tables['year'].select().where(
                metadata.tables['year'].c.yID == year['yID'])).one()
            self.assertEqual(row.yearFrom, date(2026, 3, 1))

    async def test_create_survey_inserts_auto_increment_plain_rows(self):
        await self.login()
        status, _, created = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'university',
            'start_year': 2027,
            'start_month': 2,
            'end_year': 2027,
            'end_month': 2,
            'status': 1,
            'groups': [
                {
                    'title': 'Digital foundations',
                    'description': 'Core infrastructure',
                    'questions': ['Fiber connection', 'Computer lab'],
                },
                {'title': 'Skills', 'questions': ['Staff training']},
            ],
        })
        self.assertEqual(status, 201, created)
        self.assertGreater(created['year_id'], 0)
        self.assertEqual(created['question_count'], 3)
        self.assertEqual(len(created['groups']), 2)
        self.assertEqual([len(group['question_ids']) for group in created['groups']], [2, 1])
        for group in created['groups']:
            self.assertGreater(group['qTID'], 0)
            self.assertTrue(all(question_id > 0 for question_id in group['question_ids']))

        with self.sessions() as db:
            year_table = metadata.tables['year']
            year_row = db.native.execute(
                select(year_table).where(year_table.c.yID == created['year_id'])
            ).one()
            self.assertEqual(year_row.yearFrom, date(2027, 2, 1))
            self.assertEqual(year_row.yearTo, date(2027, 2, 1))
            self.assertEqual(year_row.status, 1)

            title_table = metadata.tables['questiontitle']
            title_ids = [group['qTID'] for group in created['groups']]
            title_rows = db.native.execute(
                select(title_table).where(title_table.c.qTID.in_(title_ids))
            ).all()
            self.assertEqual({row.qTDetail for row in title_rows}, {'Digital foundations', 'Skills'})
            descriptions = {row.qTDetail: row.description for row in title_rows}
            self.assertEqual(descriptions['Digital foundations'], 'Core infrastructure')
            self.assertIsNone(descriptions['Skills'])
            self.assertTrue(all(not (row.description or '').startswith('{') for row in title_rows))

            question_table = metadata.tables['uniquestion']
            question_rows = db.native.execute(
                select(question_table).where(question_table.c.yID == created['year_id'])
            ).all()
            self.assertEqual(
                {row.uQDetail for row in question_rows},
                {'Fiber connection', 'Computer lab', 'Staff training'},
            )
            self.assertTrue(all(row.qTID in set(title_ids) for row in question_rows))

    async def test_create_survey_creates_new_year_and_routes_ministry_questions(self):
        await self.login()
        status, _, created = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'ministry',
            'start_year': 2028,
            'start_month': 4,
            'end_year': 2028,
            'end_month': 4,
            'groups': [{'title': 'Ministry capacity', 'questions': ['Policy readiness']}],
        })
        self.assertEqual(status, 201, created)
        self.assertGreater(created['year_id'], 0)
        self.assertGreater(created['groups'][0]['qTID'], 0)

        with self.sessions() as db:
            ministry_table = metadata.tables['ministryquestion']
            row = db.native.execute(
                select(ministry_table).where(ministry_table.c.yID == created['year_id'])
            ).one()
            self.assertEqual(row.mQDetail, 'Policy readiness')
            self.assertGreater(row.mQId, 0)
            self.assertEqual(row.qTID, created['groups'][0]['qTID'])
            self.assertEqual(
                db.native.execute(
                    select(func.count()).select_from(metadata.tables['uniquestion']).where(
                        metadata.tables['uniquestion'].c.yID == created['year_id']
                    )
                ).scalar(),
                0,
            )

    async def test_survey_forms_count_distinct_question_titles_per_audience(self):
        await self.login()
        status, _, created = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'university',
            'start_year': 2031,
            'start_month': 5,
            'end_year': 2031,
            'end_month': 5,
            'groups': [
                {'title': 'Infrastructure', 'questions': ['Fiber connection', 'Computer lab']},
                {'title': 'Skills', 'questions': ['Staff training']},
            ],
        })
        self.assertEqual(status, 201, created)
        # A third question joins the existing "Infrastructure" title, so the
        # year keeps 2 distinct titles across 3 question rows.
        status, _, question = await self.admin_request('/survey/questions/university', 'POST', {
            'yID': created['year_id'],
            'qTID': created['groups'][0]['qTID'],
            'uQDetail': 'Wireless coverage',
        })
        self.assertEqual(status, 201, question)

        status, _, forms = await self.admin_request(
            f"/survey/forms?org_type=university&year_id={created['year_id']}&limit=100")
        self.assertEqual(status, 200, forms)
        self.assertEqual([form['year_id'] for form in forms], [created['year_id']])
        # 4 questions across only 2 distinct titles: the count must not
        # report one title per question row.
        self.assertEqual(forms[0]['question_count'], 4)
        self.assertEqual(forms[0]['question_title_count'], 2)

        status, _, ministry = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'ministry',
            'start_year': 2031,
            'start_month': 8,
            'end_year': 2031,
            'end_month': 8,
            'groups': [
                {'title': 'Capacity', 'questions': ['Policy readiness']},
                {'title': 'Oversight', 'questions': ['Audit plan', 'Reporting']},
            ],
        })
        self.assertEqual(status, 201, ministry)

        status, _, forms = await self.admin_request(
            f"/survey/forms?org_type=ministry&year_id={ministry['year_id']}&limit=100")
        self.assertEqual(status, 200, forms)
        self.assertEqual([form['year_id'] for form in forms], [ministry['year_id']])
        self.assertEqual(forms[0]['question_count'], 3)
        self.assertEqual(forms[0]['question_title_count'], 2)

    async def test_survey_forms_org_type_filter_returns_only_matching_audiences(self):
        await self.login()
        status, _, university = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'university',
            'start_year': 2032,
            'start_month': 6,
            'end_year': 2032,
            'end_month': 6,
            'groups': [{'title': 'Campus', 'questions': ['Dormitories']}],
        })
        self.assertEqual(status, 201, university)
        status, _, ministry = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'ministry',
            'start_year': 2032,
            'start_month': 7,
            'end_year': 2032,
            'end_month': 7,
            'groups': [{'title': 'Budgets', 'questions': ['Allocations']}],
        })
        self.assertEqual(status, 201, ministry)
        self.assertNotEqual(ministry['year_id'], university['year_id'])

        status, _, university_only = await self.admin_request('/survey/forms?org_type=university&limit=100')
        self.assertEqual(status, 200, university_only)
        self.assertTrue(university_only)
        self.assertTrue(all(form['org_type'] == 'university' for form in university_only))
        self.assertIn(university['year_id'], [form['year_id'] for form in university_only])
        self.assertNotIn(ministry['year_id'], [form['year_id'] for form in university_only])

        status, _, ministry_only = await self.admin_request('/survey/forms?org_type=ministry&limit=100')
        self.assertEqual(status, 200, ministry_only)
        self.assertTrue(ministry_only)
        self.assertTrue(all(form['org_type'] == 'ministry' for form in ministry_only))
        self.assertIn(ministry['year_id'], [form['year_id'] for form in ministry_only])
        self.assertNotIn(university['year_id'], [form['year_id'] for form in ministry_only])

    async def test_create_survey_rejects_invalid_year_range_without_writing_titles(self):
        await self.login()
        with self.sessions() as db:
            before = db.native.execute(
                select(func.count()).select_from(metadata.tables['questiontitle'])
            ).scalar()
        # start > end should be rejected
        status, _, body = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'university',
            'start_year': 2028,
            'start_month': 1,
            'end_year': 2027,
            'end_month': 1,
            'groups': [{'title': 'Should not exist', 'questions': ['Nope']}],
        })
        self.assertEqual(status, 422, body)
        with self.sessions() as db:
            after = db.native.execute(
                select(func.count()).select_from(metadata.tables['questiontitle'])
            ).scalar()
        self.assertEqual(after, before)

    async def test_create_survey_validates_year_choice_and_questions(self):
        await self.login()
        status, _, _ = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'university', 'year': 2027,
            'groups': [{'title': 'Empty', 'questions': ['   ']}],
        })
        self.assertEqual(status, 422)
        status, _, _ = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'university', 'year': 2027, 'year_id': 1,
            'groups': [{'title': 'Both years', 'questions': ['Text']}],
        })
        self.assertEqual(status, 422)
        status, _, _ = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'university', 'year': 2027, 'groups': [],
        })
        self.assertEqual(status, 422)

    async def test_organization_directory_pages_are_reachable(self):
        await self.login()
        for path, title in (
            ("/dashboard/departments", "တက္ကသိုလ်များ"),
            ("/dashboard/ministries", "ဝန်ကြီးဌာနများ"),
        ):
            status, _, body = await self.request(path)
            self.assertEqual(status, 200, path)
            self.assertIn(f'href="{path}"', body, path)
            self.assertIn(title, body, path)

    async def test_removed_dashboard_pages_are_unavailable_and_unlinked(self):
        await self.login()
        for path in ("/dashboard/audit", "/dashboard/data", "/dashboard/users"):
            status, _, body = await self.request(path)
            self.assertEqual(status, 404, path)
            self.assertIn("Page not found", body)

        status, _, body = await self.request("/dashboard")
        self.assertEqual(status, 200)
        for path in ("/dashboard/audit", "/dashboard/data", "/dashboard/users"):
            self.assertNotIn(path, body)

    async def test_builder_page_is_removed_and_the_api_stays_protected(self):
        status, _, _ = await self.request('/dashboard/survey-builder')
        self.assertEqual(status, 303)
        status, _, _ = await self.request('/api/admin/survey/years')
        self.assertEqual(status, 401)
        await self.login()
        status, _, body = await self.request('/dashboard/survey-builder')
        self.assertEqual(status, 404)
        self.assertIn('Page not found', body)
        status, _, body = await self.request('/dashboard/forms')
        self.assertEqual(status, 200)
        self.assertNotIn('survey-builder', body)
        status, _, _ = await self.request('/dashboard')
        self.assertEqual(status, 200)
        status, _, _ = await self.admin_request('/survey/years', 'POST', {
            'year_from': 3, 'year_to': 2026, 'status': 1,
        }, csrf=False)
        self.assertEqual(status, 403)

    async def test_question_groups_update_and_delete_within_one_year(self):
        await self.login()
        status, _, created = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'university',
            'start_year': 2033,
            'start_month': 1,
            'end_year': 2033,
            'end_month': 1,
            'groups': [
                {'title': 'Group one', 'questions': ['First question', 'Second question']},
                {'title': 'Group two', 'questions': ['Third question']},
            ],
        })
        self.assertEqual(status, 201, created)
        year_id = created['year_id']
        first_title_id = created['groups'][0]['qTID']

        status, _, groups = await self.admin_request(f"/survey/builder/groups/university/{year_id}")
        self.assertEqual(status, 200, groups)
        self.assertEqual([group['qTDetail'] for group in groups['groups']], ['Group one', 'Group two'])
        first_questions = groups['groups'][0]['questions']
        self.assertEqual([question['detail'] for question in first_questions],
                         ['First question', 'Second question'])

        status, _, _ = await self.admin_request("/survey/builder/groups/university/999999")
        self.assertEqual(status, 404)

        updated = {
            'title': 'Group one renamed',
            'questions': [
                {'id': first_questions[0]['id'], 'detail': 'First question fixed'},
                {'id': first_questions[1]['id'], 'detail': 'Second question fixed'},
            ],
        }
        status, _, payload = await self.admin_request(
            f"/survey/builder/groups/university/{year_id}/{first_title_id}", 'PUT', updated,
        )
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload['qTDetail'], 'Group one renamed')
        self.assertEqual(payload['qTID'], first_title_id)
        self.assertEqual([question['detail'] for question in payload['questions']],
                         ['First question fixed', 'Second question fixed'])

        # Rewriting with a subset drops the missing questions.
        status, _, payload = await self.admin_request(
            f"/survey/builder/groups/university/{year_id}/{first_title_id}", 'PUT',
            {**updated, 'questions': updated['questions'][:1]},
        )
        self.assertEqual(status, 200, payload)
        self.assertEqual([question['detail'] for question in payload['questions']],
                         ['First question fixed'])
        dropped_id = first_questions[1]['id']
        with self.sessions() as db:
            question_table = metadata.tables['uniquestion']
            self.assertIsNone(db.native.execute(
                select(question_table).where(question_table.c.uQId == dropped_id)
            ).first())

        # An unknown id, an empty question list, or duplicate ids are rejected.
        status, _, payload = await self.admin_request(
            f"/survey/builder/groups/university/{year_id}/{first_title_id}", 'PUT',
            {'title': updated['title'], 'questions': [
                {'id': first_questions[0]['id'], 'detail': 'x'},
                {'id': 999999, 'detail': 'Extra'},
            ]},
        )
        self.assertEqual(status, 400, payload)
        status, _, payload = await self.admin_request(
            f"/survey/builder/groups/university/{year_id}/{first_title_id}", 'PUT',
            {'title': updated['title'], 'questions': []},
        )
        self.assertEqual(status, 422, payload)
        status, _, payload = await self.admin_request(
            f"/survey/builder/groups/university/{year_id}/{first_title_id}", 'PUT',
            {'title': updated['title'], 'questions': [
                {'id': first_questions[0]['id'], 'detail': 'x'},
                {'id': first_questions[0]['id'], 'detail': 'y'},
            ]},
        )
        self.assertEqual(status, 422, payload)

        # Questions without an id are inserted under the title.
        status, _, payload = await self.admin_request(
            f"/survey/builder/groups/university/{year_id}/{first_title_id}", 'PUT',
            {'title': updated['title'], 'questions': [
                {'id': first_questions[0]['id'], 'detail': 'First question fixed'},
                {'detail': 'Fourth question'},
                {'detail': 'Fifth question'},
            ]},
        )
        self.assertEqual(status, 200, payload)
        added_ids = [question['id'] for question in payload['questions'][1:]]
        self.assertEqual(len(set(added_ids)), 2, payload)
        self.assertNotIn(first_questions[0]['id'], added_ids)

        status, _, groups = await self.admin_request(f"/survey/builder/groups/university/{year_id}")
        self.assertEqual([group['qTDetail'] for group in groups['groups']],
                         ['Group one renamed', 'Group two'])
        self.assertEqual(
            [question['detail'] for question in groups['groups'][0]['questions']],
            ['First question fixed', 'Fourth question', 'Fifth question'],
        )
        self.assertEqual(
            [question['detail'] for question in groups['groups'][1]['questions']],
            ['Third question'],
        )

        status, _, _ = await self.admin_request(
            f"/survey/builder/groups/university/{year_id}/{first_title_id}", 'DELETE',
        )
        self.assertEqual(status, 204)
        status, _, payload = await self.admin_request(
            f"/survey/builder/groups/university/{year_id}/{first_title_id}", 'DELETE',
        )
        self.assertEqual(status, 404)

        status, _, groups = await self.admin_request(f"/survey/builder/groups/university/{year_id}")
        self.assertEqual([group['qTDetail'] for group in groups['groups']], ['Group two'])

        with self.sessions() as db:
            question_table = metadata.tables['uniquestion']
            rows = db.native.execute(
                select(question_table).where(question_table.c.yID == year_id)
            ).all()
            self.assertEqual([row.uQDetail for row in rows], ['Third question'])
            title_table = metadata.tables['questiontitle']
            remaining = db.native.execute(
                select(title_table.c.qTDetail).where(
                    title_table.c.qTID == first_title_id)
            ).first()
            self.assertIsNone(remaining)

    async def test_shared_question_title_scopes_rename_and_delete_to_its_year(self):
        await self.login()
        status, _, holder = await self.admin_request('/survey/forms/create', 'POST', {
            'org_type': 'university',
            'start_year': 2035,
            'start_month': 1,
            'end_year': 2035,
            'end_month': 1,
            'groups': [{'title': 'Shared heading', 'questions': ['Holder question']}],
        })
        self.assertEqual(status, 201, holder)
        shared_title_id = holder['groups'][0]['qTID']

        status, _, other_year = await self.admin_request('/survey/years', 'POST', {
            'year_from': 3, 'year_to': 2036, 'status': 1,
        })
        self.assertEqual(status, 201, other_year)
        status, _, shared_question = await self.admin_request('/survey/questions/university', 'POST', {
            'yID': other_year['yID'], 'qTID': shared_title_id, 'uQDetail': 'Sharing question',
        })
        self.assertEqual(status, 201, shared_question)

        renamed = {
            'title': 'Renamed heading',
            'questions': [
                {'id': shared_question['uQId'], 'detail': 'Sharing question fixed'},
                {'detail': 'Sharing question added'},
            ],
        }
        status, _, payload = await self.admin_request(
            f"/survey/builder/groups/university/{other_year['yID']}/{shared_title_id}",
            'PUT', renamed,
        )
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload['qTDetail'], 'Renamed heading')
        cloned_title_id = payload['qTID']
        self.assertNotEqual(cloned_title_id, shared_title_id)
        self.assertEqual([question['detail'] for question in payload['questions']],
                         ['Sharing question fixed', 'Sharing question added'])
        self.assertNotEqual(payload['questions'][1]['id'], shared_question['uQId'])

        status, _, holder_groups = await self.admin_request(
            f"/survey/builder/groups/university/{holder['year_id']}",
        )
        self.assertEqual(status, 200, holder_groups)
        self.assertEqual(holder_groups['groups'][0]['qTID'], shared_title_id)
        self.assertEqual(holder_groups['groups'][0]['qTDetail'], 'Shared heading')
        self.assertEqual(
            [question['detail'] for question in holder_groups['groups'][0]['questions']],
            ['Holder question'],
        )

        # Both the re-pointed and the newly inserted question follow the clone.
        with self.sessions() as db:
            question_table = metadata.tables['uniquestion']
            rows = db.native.execute(
                select(question_table).where(question_table.c.yID == other_year['yID'])
            ).all()
            self.assertEqual({row.qTID for row in rows}, {cloned_title_id})

        status, _, _ = await self.admin_request(
            f"/survey/builder/groups/university/{other_year['yID']}/{cloned_title_id}",
            'DELETE',
        )
        self.assertEqual(status, 204)
        status, _, other_groups = await self.admin_request(
            f"/survey/builder/groups/university/{other_year['yID']}",
        )
        self.assertEqual(other_groups['groups'], [])

        with self.sessions() as db:
            question_table = metadata.tables['uniquestion']
            holder_rows = db.native.execute(
                select(question_table).where(question_table.c.yID == holder['year_id'])
            ).all()
            self.assertEqual([row.uQDetail for row in holder_rows], ['Holder question'])
            self.assertEqual(
                db.native.execute(
                    select(func.count()).select_from(question_table).where(
                        question_table.c.yID == other_year['yID'])
                ).scalar(),
                0,
            )
            title_table = metadata.tables['questiontitle']
            shared = db.native.execute(
                select(title_table.c.qTDetail).where(title_table.c.qTID == shared_title_id)
            ).scalar()
            self.assertEqual(shared, 'Shared heading')
            orphaned = db.native.execute(
                select(title_table.c.qTID).where(title_table.c.qTID == cloned_title_id)
            ).first()
            self.assertIsNone(orphaned)



class PrivateDashboardRecoveryTests(DashboardRecoveryTests):
    metadata_storage = 'private'
