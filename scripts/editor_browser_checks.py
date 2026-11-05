"""End-to-end question suggestions, reusable definitions and dashboard empty states."""
from pathlib import Path


def check(page, context, base):
    output = Path('/tmp/dedc-question-editor-review')
    output.mkdir(exist_ok=True)
    page.goto(base + '/dashboard/departments')
    page.get_by_role('heading', name='No departments added yet', exact=True).wait_for()
    page.get_by_role('button', name='Add your first department', exact=True).click()
    assert page.locator('select[name=org_type]').input_value() == ''
    assert page.locator('input[name=name]').is_visible()
    assert not page.locator('input[name=uni_type]').is_visible()
    page.get_by_role('button', name='Close dialog').click()
    for width in (1440, 768, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.screenshot(path=str(output / f'departments-empty-{width}.png'), full_page=True, animations='disabled')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    token = page.locator('meta[name=csrf-token]').get_attribute('content')
    headers = {'X-CSRF-Token': token}

    def post(path, data):
        response = context.request.post(base + '/api/admin' + path, headers=headers, data=data)
        assert response.ok, response.text()
        return response.json()

    saved = post('/question-library', {
        'key': 'institution', 'title': 'Which institution do you represent?',
        'kind': 'single_choice', 'required': True,
        'options': [{'value': 'public', 'label': 'Public'}, {'value': 'private', 'label': 'Private'}],
    })
    form = post('/forms', {'title': 'Question suggestion browser check'})
    form_id = form['id']
    version_id = form['versions'][0]['id']
    response = context.request.put(base + f'/api/admin/forms/{form_id}/versions/{version_id}', headers=headers, data={
        'title': form['title'], 'revision': 1, 'sections': [],
    })
    assert response.ok, response.text()
    page.goto(base + f'/dashboard/forms/{form_id}')
    page.get_by_role('button', name='Add question', exact=True).click()
    page.get_by_label('Question title', exact=True).fill('How many students are enrolled?')
    page.get_by_text('No saved question matches.', exact=False).wait_for()
    result = context.request.get(base + '/api/admin/question-library?search=How%20many%20students').json()
    assert result['total'] == 0, 'Typing must not insert unfinished questions'
    page.locator('#question-form select[name=kind]').select_option('number')
    page.get_by_label('Minimum value', exact=True).fill('0')
    # Errors retain the question and do not add anything to the local draft.
    page.route('**/api/admin/question-library', lambda route: route.fulfill(status=503, content_type='application/json', body='{"detail":"Please retry saving your question."}'))
    page.get_by_role('button', name='Save question', exact=True).click()
    page.get_by_text('Please retry saving your question.', exact=True).wait_for()
    assert page.get_by_label('Question title', exact=True).input_value() == 'How many students are enrolled?'
    page.unroute('**/api/admin/question-library')
    page.get_by_role('button', name='Save question', exact=True).click()
    page.locator('[data-question="0:0"]').wait_for()
    page.get_by_role('button', name='Save changes', exact=True).click()
    page.get_by_text('All changes saved', exact=True).wait_for()
    # This is the Add question button that previously raised syncMeta errors.
    page.locator('[data-add-question="0"]').click()
    title = page.get_by_label('Question title', exact=True)
    title.fill('institution')
    suggestion = page.get_by_role('button', name='Which institution do you represent?', exact=False)
    suggestion.wait_for()
    assert title.input_value() == 'institution'
    for width in (1440, 768, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.screenshot(path=str(output / f'question-suggestions-{width}.png'), full_page=True, animations='disabled')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    suggestion.click()
    assert page.locator('#question-form select[name=kind]').input_value() == 'single_choice'
    assert page.get_by_label('Required', exact=True).is_checked()
    assert page.locator('#question-form textarea[name=options]').input_value() == 'public | Public\nprivate | Private'
    page.get_by_role('button', name='Save & add another', exact=True).click()
    page.locator('[data-question="0:1"]').wait_for()
    assert page.locator('#question-form textarea[name=title]').input_value() == ''
    page.get_by_role('button', name='Close dialog').click()
    page.set_viewport_size({'width': 1440, 'height': 1000})
    # Edit an existing question after selecting a suggestion; its own key is valid.
    page.locator('[data-edit-question="0:1"]').click()
    title = page.get_by_label('Question title', exact=True)
    title.fill('institution')
    page.get_by_role('button', name='Which institution do you represent?', exact=False).click()
    page.get_by_role('button', name='Save question', exact=True).click()
    page.get_by_role('dialog').wait_for(state='hidden')
    page.get_by_role('button', name='Save changes', exact=True).click()
    page.get_by_text('All changes saved', exact=True).wait_for()
    page.reload()
    page.locator('[data-question="0:1"]').wait_for()
    definition = context.request.get(base + f'/api/admin/forms/{form_id}').json()['versions'][0]
    questions = definition['sections'][0]['questions']
    assert len(questions) == 2
    assert questions[0]['config']['min'] == 0
    assert questions[1]['options'] == saved['question']['options']
    result = context.request.get(base + '/api/admin/question-library?search=institution').json()
    assert result['total'] == 1, result
    # Cancelled text is never inserted into the library.
    page.locator('[data-add-question="0"]').click()
    page.get_by_label('Question title', exact=True).fill('An unfinished question to cancel')
    page.get_by_role('button', name='Close dialog').click()
    assert context.request.get(base + '/api/admin/question-library?search=unfinished').json()['total'] == 0
    for width in (1440, 768, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        for route, selector in (
            ('', '#content .stats'), ('/forms', '#content .panel'),
            ('/departments', '#content .organization-grid'), ('/reports', '#content .panel'),
            ('/users', '#content table'), ('/data', '#content .panel'),
            ('/audit', '#content table'), ('/settings', '#theme-setting'),
            (f'/forms/{form_id}', '#content .editor-layout'),
            (f'/forms/{form_id}/preview', '#content .survey-shell'),
        ):
            page.goto(base + '/dashboard' + route)
            if route.endswith('/preview'):
                page.locator('#content .skeleton').wait_for(state='detached')
            else:
                page.locator(selector).first.wait_for()
            if route == '' and width <= 1080:
                toggle = page.locator('[data-sidebar-toggle]')
                assert toggle.get_attribute('aria-expanded') == 'false'
                toggle.click()
                assert toggle.get_attribute('aria-expanded') == 'true'
                page.keyboard.press('Escape')
                assert toggle.get_attribute('aria-expanded') == 'false'
            assert page.locator('#content > .notice.error').count() == 0, (route, page.locator('#content').inner_text())
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, route)
            page.screenshot(path=str(output / f'{route.strip("/").replace("/", "-") or "overview"}-{width}.png'), full_page=True, animations='disabled')
    page.goto(base + '/dashboard/settings')
    page.locator('#theme-setting').select_option('dark')
    page.goto(base + '/dashboard/departments')
    page.locator('.organization-grid').wait_for()
    page.screenshot(path=str(output / 'departments-dark.png'), full_page=True, animations='disabled')
    page.goto(base + '/dashboard/settings')
    page.locator('#theme-setting').select_option('light')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.goto(base + '/dashboard')
    page.locator('#content .stats').wait_for()
    print('PASS: existing-section add, live suggestions, new-question persistence, reuse with choices, duplicate prevention, edit/retry/cancel, empty departments, all dashboard routes at three widths and dark theme', flush=True)
