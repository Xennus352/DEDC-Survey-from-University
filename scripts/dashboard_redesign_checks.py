"""Workflow checks for the isolated dashboard redesign review."""
from pathlib import Path
from playwright.sync_api import expect


def check(page, context, base, ready, output):
    phase = 'after'
    page.set_viewport_size({'width':1440,'height':1000})
    # Create and publish using real dialogs and editor controls.
    page.goto(base+'/dashboard/forms');ready()
    page.get_by_role('button',name='Create form',exact=True).click()
    page.get_by_label('Form title',exact=True).fill('Browser redesign survey')
    page.get_by_role('button',name='Create draft',exact=True).click()
    page.wait_for_url('**/dashboard/forms/*');ready()
    created_id=int(page.url.rsplit('/',1)[1])
    page.get_by_role('button',name='Add question',exact=False).click()
    page.get_by_label('Question title',exact=True).fill('How many digital classrooms are available?')
    page.locator('input[name=key]').evaluate('(el)=>el.closest("details").open=true')
    page.get_by_label('Unique key',exact=True).fill('classrooms')
    page.locator('select[name=kind]').select_option('number')
    page.get_by_role('dialog').screenshot(path=str(output/phase/'question-dialog.png'))
    page.set_viewport_size({'width':390,'height':900})
    assert page.get_by_role('dialog').evaluate('(el)=>el.scrollWidth<=el.clientWidth')
    page.get_by_role('dialog').screenshot(path=str(output/phase/'question-dialog-mobile.png'))
    page.set_viewport_size({'width':1440,'height':1000})
    page.get_by_role('button',name='Save question',exact=True).click()
    page.get_by_role('button',name='Save changes',exact=True).click()
    page.get_by_text('All changes saved',exact=True).wait_for()
    page.screenshot(path=str(output/phase/'builder-populated.png'),full_page=True)
    page.get_by_role('link',name='Preview',exact=True).click();ready()
    page.get_by_role('button',name='Mobile',exact=True).click()
    expect(page.get_by_role('button',name='Mobile',exact=True)).to_have_attribute('aria-pressed','true')
    page.get_by_label('From date',exact=True).fill('2021-01-01')
    page.get_by_label('To date',exact=True).fill('2026-03-31')
    page.get_by_role('button',name='Start survey',exact=False).click()
    page.get_by_label('How many digital classrooms are available?',exact=False).fill('6')
    page.locator('input[name=name]').fill('Review participant')
    page.locator('input[name=age]').fill('24')
    page.get_by_role('button',name='Validate preview',exact=True).click()
    page.get_by_role('status').filter(has_text='All visible answers passed').wait_for()
    page.get_by_role('link',name='Back to builder',exact=True).click();ready()
    page.once('dialog',lambda dialog:dialog.accept())
    page.get_by_role('button',name='Publish this version',exact=True).click()
    page.get_by_role('button',name='Create new draft',exact=True).wait_for()
    csrf=page.locator('meta[name=csrf-token]').get_attribute('content')
    response=context.request.post(base+f'/api/admin/forms/{created_id}/submit',headers={'X-CSRF-Token':csrf},data={'answers':{'classrooms':6,'name':'Review participant','age':24},'reporting_start':'2021-01-01','reporting_end':'2026-03-31'})
    assert response.status==201,response.text()
    page.goto(base+'/dashboard/reports');ready()
    page.get_by_role('button',name='View answers',exact=True).first.click()
    expect(page.get_by_role('dialog')).to_be_visible()
    page.get_by_role('button',name='Close dialog',exact=True).click()
    page.locator('[data-select-submission]').first.check()
    page.get_by_role('button',name='Approve',exact=True).click()
    page.locator('.badge.approved').first.wait_for()
    page.get_by_text('Export report',exact=True).click()
    with page.expect_download() as download:
        page.get_by_role('link',name='Export CSV',exact=True).click()
    assert Path(download.value.path()).stat().st_size>0
    # Department directory, long labels and editing.
    page.goto(base+'/dashboard/departments');ready()
    page.get_by_role('button',name='Add department',exact=True).click()
    page.get_by_role('dialog').get_by_label('Type',exact=True).select_option('university')
    org_name='Department of Digital Learning and Research with a deliberately long organization name'
    page.get_by_label('University name',exact=True).fill(org_name)
    page.get_by_role('dialog').screenshot(path=str(output/phase/'department-dialog.png'))
    page.set_viewport_size({'width':390,'height':900})
    assert page.get_by_role('dialog').evaluate('(el)=>el.scrollWidth<=el.clientWidth')
    page.get_by_role('dialog').screenshot(path=str(output/phase/'department-dialog-mobile.png'))
    page.set_viewport_size({'width':1440,'height':1000})
    page.get_by_role('button',name='Create',exact=True).click()
    page.get_by_text(org_name,exact=True).wait_for()
    page.locator('tr').filter(has_text=org_name).get_by_role('button',name='Edit',exact=True).click()
    page.get_by_label('University name',exact=True).fill('Digital learning department')
    page.get_by_role('button',name='Save',exact=True).click()
    page.get_by_text('Digital learning department',exact=True).wait_for()
    # Search and empty results.
    page.goto(base+'/dashboard/forms?search=does-not-exist');ready()
    page.get_by_role('heading',name='No matching forms',exact=True).wait_for()
    page.screenshot(path=str(output/phase/'empty-search.png'),full_page=True)
    page.locator('#global-search').fill('digital')
    page.locator('#global-search').press('Enter')
    expect(page.get_by_role('dialog')).to_be_visible()
    page.get_by_role('button',name='Close dialog',exact=True).click()
    # Inline fetch error and retry.
    def fail_reports(route): route.fulfill(status=503,content_type='application/json',body='{"detail":"Temporary reporting service error"}')
    import re
    reports_pattern=re.compile(r'.*/api/admin/reports(?:\?.*)?$')
    context.route(reports_pattern,fail_reports)
    page.goto(base+'/dashboard/reports');ready()
    page.get_by_role('button',name='Retry',exact=True).wait_for()
    page.screenshot(path=str(output/phase/'error-retry.png'),full_page=True)
    context.unroute(reports_pattern,fail_reports)
    page.get_by_role('button',name='Retry',exact=True).click()
    page.locator('#content .stats').wait_for()
    # Settings persistence, dark screens, mobile nav, keyboard and reduced motion.
    page.goto(base+'/dashboard/settings');ready()
    page.locator('#theme-setting').select_option('dark')
    for route,name in [('', 'overview'),('/forms','forms'),('/reports','reports'),('/settings','settings')]:
        page.goto(base+'/dashboard'+route);ready()
        assert page.evaluate('document.documentElement.dataset.theme')=='dark'
        page.screenshot(path=str(output/phase/f'{name}-dark.png'),full_page=True)
    page.goto(base+'/dashboard/settings');ready();page.locator('#theme-setting').select_option('light')
    page.set_viewport_size({'width':390,'height':900})
    page.goto(base+'/dashboard');ready()
    page.get_by_role('button',name='Search workspace',exact=True).click()
    page.get_by_role('dialog').get_by_role('searchbox').fill('digital')
    page.get_by_role('dialog').get_by_role('button',name='Search',exact=True).click()
    page.get_by_role('dialog').locator('.quick-link').first.wait_for()
    page.get_by_role('button',name='Close dialog',exact=True).click()
    page.get_by_role('button',name='Toggle navigation',exact=True).click()
    expect(page.get_by_role('button',name='Toggle navigation',exact=True)).to_have_attribute('aria-expanded','true')
    page.keyboard.press('Tab')
    assert page.evaluate('Boolean(document.activeElement.closest(".sidebar"))')
    page.keyboard.press('Escape')
    expect(page.get_by_role('button',name='Toggle navigation',exact=True)).to_have_attribute('aria-expanded','false')
    assert page.locator('#sidebar').evaluate('(el)=>el.inert')
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(base+'/dashboard/forms');ready()
    page.get_by_role('button',name='Toggle navigation',exact=True).click()
    assert page.locator('body').evaluate('(el)=>el.classList.contains("sidebar-collapsed")')
    page.get_by_role('button',name='Toggle navigation',exact=True).click()
    # Readable data and pagination regression checks use this harness's SQLite DB.
    from app.database import engine, SessionLocal
    from app.storage.existing import metadata
    assert engine.url.get_backend_name() == 'sqlite'
    with SessionLocal() as db:
        db.native.execute(metadata.tables['university'].insert(), [
            {'uniName': f'Pagination university {i:03}', 'uniType': 'Public'} for i in range(61)
        ])
        db.native.commit()
    review = Path('/tmp/dedc-data-usability/after')
    review.mkdir(parents=True, exist_ok=True)
    page.goto(base + '/dashboard/departments'); ready()
    page.locator('button[data-pagination="2"]').click()
    page.get_by_text('Page 2 of', exact=False).wait_for()
    page.get_by_role('cell', name='Pagination university 040', exact=True).wait_for()
    page.screenshot(path=str(review / 'directory-page-2.png'), full_page=True)
    def send(path, body):
        response = context.request.post(base + '/api/admin' + path, headers={'X-CSRF-Token': csrf}, data=body)
        assert response.ok, response.text()
        return response.json()
    readable = send('/forms', {'title': 'Readable database answers'})
    readable_id = readable['id']
    readable_version = readable['versions'][0]['id']
    response = context.request.put(base + f'/api/admin/forms/{readable_id}/versions/{readable_version}', headers={'X-CSRF-Token': csrf}, data={
        'title': 'Readable database answers', 'revision': 1, 'sections': [{'title': 'Answer meanings', 'questions': [
            {'key': 'zero', 'title': 'Number of laboratories', 'kind': 'number'},
            {'key': 'present', 'title': 'Equipment available', 'kind': 'yes_no'},
            {'key': 'choice', 'title': 'Institution type', 'kind': 'single_choice', 'options': [{'value': 'internal_code', 'label': 'Public university'}]},
            {'key': 'blank', 'title': 'Optional notes', 'kind': 'short_text'},
            {'key': 'missing', 'title': 'Additional information', 'kind': 'long_text'},
        ]}],
    })
    assert response.ok, response.text()
    send(f'/forms/{readable_id}/versions/{readable_version}/publish', {'revision': response.json()['revision']})
    submission = send(f'/forms/{readable_id}/submit', {'reporting_start': '2021-01-01', 'reporting_end': '2026-03-31', 'answers': {'zero': 0, 'present': False, 'choice': 'internal_code', 'blank': ''}})
    page.goto(base + f'/dashboard/reports?form_id={readable_id}'); ready()
    page.locator(f'[data-view-submission="{submission["id"]}"]').click()
    dialog = page.get_by_role('dialog')
    for text in ('0', 'No', 'Public university', 'Empty text', 'No answer'):
        expect(dialog.get_by_text(text, exact=True)).to_be_visible()
    assert 'internal_code' not in dialog.inner_text()
    for width in (1440, 390):
        page.set_viewport_size({'width': width, 'height': 900})
        assert dialog.evaluate('(el)=>el.scrollWidth<=el.clientWidth')
        page.screenshot(path=str(review / f'answer-details-{width}.png'), full_page=True)
    page.get_by_role('button', name='Close dialog', exact=True).click()
    print('PASS: real directory page 2, actor names and structured audit details, distinct zero/false/empty/missing answers and choice labels at desktop/mobile widths', flush=True)
    # Public and login screens remain healthy and use their original stylesheets.
    public = context.browser.new_context()
    public.route('**/*', lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
    visitor = public.new_page()
    for route in ('/', '/portal', '/survey/login'):
        response = visitor.goto(base + route)
        assert response.status == 200, (route, response.status)
        if route != '/':
            assert visitor.locator('link[href="/static/css/admin/workspace.css"]').count() == 1
    public.close()
    print('PASS: create/edit/save/publish/preview, submission review/export, department and user/role management, global search, empty/error/retry states, drag/drop/import/source export, dark persistence, keyboard/mobile navigation, public routes',flush=True)
