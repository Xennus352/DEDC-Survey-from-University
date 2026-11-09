"""Exercise dashboard recovery with temporary ten-table data and a real browser.

Run: METADATA_STORAGE=sql uv run --with playwright python scripts/check_dashboard_recovery.py
The shared review fixture captures every route at desktop, tablet and phone widths.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_dashboard_redesign
import dashboard_redesign_checks


def check(page, context, base, ready, output):
    failures = []
    page.on('response', lambda r: failures.append((r.status, r.url))
            if '/api/admin/' in r.url and r.status >= 400 else None)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    for route in ('/', '/portal'):
        assert context.request.get(base + route).status == 200
    page.goto(base + '/dashboard/survey-builder')
    ready()
    page.wait_for_function("document.querySelector('#years-table').textContent.trim().length > 0")
    page.locator('[data-dialog="year-form"][data-action="create"]').click()
    page.locator('#year-from').fill('3')
    page.locator('#year-to').fill('2026')
    page.locator('#year-status').select_option('1')
    page.locator('#year-form button[type=submit]').click()
    page.locator('#year-form-dialog').wait_for(state='hidden')
    page.locator('#years-table [data-edit-year]').first.wait_for()
    page.reload(); ready()
    page.locator('#years-table [data-edit-year]').first.click()
    assert page.locator('#year-from').input_value() == '3'
    assert page.locator('#year-to').input_value() == '2026'
    page.locator('#year-form-dialog [data-close-dialog]').first.click()
    page.locator('[data-tab="question-titles"]').click()
    page.locator('[data-dialog="title-form"][data-action="create"]').click()
    page.locator('#title-detail').fill('Digital facilities')
    page.locator('#title-form button[type=submit]').click()
    page.locator('#title-form-dialog').wait_for(state='hidden')
    page.locator('[data-tab="university-questions"]').click()
    page.locator('[data-dialog="question-form"][data-qtype="university"]').click()
    page.locator('#question-detail').fill('Computer laboratories')
    page.locator('#question-year').select_option(index=1)
    page.locator('#question-title').select_option(index=1)
    page.locator('#question-form button[type=submit]').click()
    page.locator('#question-form-dialog').wait_for(state='hidden')
    page.locator('[data-tab="builder"]').click()
    page.locator('#builder-year').select_option(index=1)
    page.locator('#load-builder').click()
    page.locator('#question-sequence .canvas-question').first.wait_for()
    # Removing and adding on a phone must work without drag-and-drop.
    page.locator('[data-remove-canvas-q]').first.click()
    page.locator('#available-questions .question-item').first.click()
    assert page.locator('#question-sequence .canvas-question').count() == 1
    page.locator('#save-form').click()
    page.wait_for_url('**/dashboard/forms/*'); ready()
    assert page.locator('.question-row').count() == 3
    form_id = page.url.rsplit('/', 1)[1]
    # Publish through the visible control, then verify persistence after navigation.
    page.locator('[data-form-toggle=status]').first.click()
    page.wait_for_function("document.querySelector('[data-form-toggle=status]').getAttribute('aria-checked') === 'true'")
    page.goto(base + '/dashboard/forms'); ready()
    toggle = page.locator(f'[data-form-id="{form_id}"][data-form-toggle=status]')
    assert toggle.get_attribute('aria-checked') == 'true'
    toggle.click()
    page.wait_for_function("!document.querySelector('[data-form-toggle=status]').disabled")
    page.reload(); ready()
    assert page.locator(f'[data-form-id="{form_id}"][data-form-toggle=status]').get_attribute('aria-checked') == 'false'
    # Soft navigation and back/forward must render their own page descriptions.
    for route in ('reports', 'users', 'forms'):
        page.locator(f'.sidebar a[href="/dashboard/{route}"]').click(); ready()
        assert page.locator('#content > .notice.error').count() == 0
    page.go_back(); ready()
    assert page.locator('body').get_attribute('data-page') == 'users'
    csrf = page.locator('meta[name=csrf-token]').get_attribute('content')
    response = context.request.post(base + '/api/admin/users', headers={'X-CSRF-Token': csrf},
                                    data={'username': 'browser-enumerator', 'role_id': 2, 'password': 'test-password-123'})
    assert response.status == 201, response.text()
    page.reload(); ready()
    assert page.locator('#content').get_by_text('browser-enumerator', exact=True).count() == 1
    for path in ('users/export/csv', 'reports/export/csv', 'reports/export/xlsx', 'reports/export/pdf'):
        response = context.request.get(base + '/api/admin/' + path)
        assert response.status == 200, (path, response.text())
        assert response.body()
    assert not failures, failures
    print('PASS: native builder CRUD, persistent form creation, publication, navigation, users and report exports', flush=True)


if __name__ == '__main__':
    dashboard_redesign_checks.check = check
    check_dashboard_redesign.main()
