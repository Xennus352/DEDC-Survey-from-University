"""Check the two-field Department flow and shared homepage brand colors."""
from pathlib import Path


def check(page, context, base):
    output = Path('/tmp/dedc-minimal-admin-review')
    output.mkdir(exist_ok=True)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.goto(base + '/dashboard/departments')
    page.get_by_role('button', name='Add department', exact=True).click()
    dialog = page.get_by_role('dialog')
    assert dialog.count() == 1
    assert dialog.get_by_label('Type', exact=True).input_value() == ''
    assert page.get_by_label('Name', exact=True).is_visible()
    assert page.get_by_label('Name', exact=True).is_enabled()
    page.get_by_role('button', name='Create', exact=True).click()
    assert dialog.is_visible(), 'Choose type is required before submission'
    dialog.get_by_label('Type', exact=True).select_option('university')
    assert page.get_by_label('University name', exact=True).is_visible()
    assert not page.locator('input[name=uni_type]').is_visible()
    page.get_by_label('University name', exact=True).fill('Minimal university')
    for width in (1440, 768, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        page.screenshot(path=str(output / f'add-department-{width}.png'), animations='disabled')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_role('button', name='Cancel', exact=True).click()
    assert page.get_by_role('cell', name='Minimal university', exact=True).count() == 0
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.get_by_role('button', name='Add department', exact=True).click()
    assert page.get_by_label('Name', exact=True).input_value() == ''
    dialog.get_by_label('Type', exact=True).select_option('university')
    page.get_by_label('University name', exact=True).fill('Minimal university')
    page.get_by_role('button', name='Create', exact=True).click()
    row = page.get_by_role('row').filter(has_text='Minimal university')
    row.get_by_role('cell', name='Unspecified', exact=True).wait_for()
    page.get_by_role('button', name='Add department', exact=True).click()
    dialog.get_by_label('Type', exact=True).select_option('ministry')
    assert page.get_by_label('Ministry name', exact=True).is_visible()
    page.get_by_label('Ministry name', exact=True).fill('Minimal ministry')
    page.get_by_role('button', name='Create', exact=True).click()
    page.get_by_role('cell', name='Minimal ministry', exact=True).wait_for()
    row = page.get_by_role('row').filter(has_text='Minimal university')
    row.get_by_role('button', name='Edit', exact=True).click()
    assert dialog.get_by_label('Type', exact=True).is_disabled()
    page.get_by_label('University name', exact=True).fill('Minimal university renamed')
    page.get_by_role('button', name='Save', exact=True).click()
    page.get_by_role('cell', name='Minimal university renamed', exact=True).wait_for()
    page.screenshot(path=str(output / 'department-directory-1440.png'), full_page=True, animations='disabled')
    # Failed requests remain in the same dialog with both field values intact.
    page.get_by_role('button', name='Add department', exact=True).click()
    dialog.get_by_label('Type', exact=True).select_option('ministry')
    page.get_by_label('Ministry name', exact=True).fill('Minimal ministry')
    page.get_by_role('button', name='Create', exact=True).click()
    page.get_by_text('Ministry with this name already exists.', exact=True).wait_for()
    assert dialog.get_by_label('Type', exact=True).input_value() == 'ministry'
    assert page.get_by_label('Ministry name', exact=True).input_value() == 'Minimal ministry'
    page.get_by_role('button', name='Cancel', exact=True).click()
    admin_brand = page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--primary").trim()')
    primary_background = page.locator('#add-org').evaluate('(el) => getComputedStyle(el).backgroundColor')
    assert primary_background == 'rgb(21, 86, 166)'
    public = context.browser.new_context(viewport={'width': 1440, 'height': 1000})
    public.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
    public_page = public.new_page()
    public_page.goto(base + '/')
    home_brand = public_page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--home-primary").trim()')
    assert home_brand == admin_brand == '#1556a6'
    public_page.screenshot(path=str(output / 'home-1440.png'), full_page=True, animations='disabled')
    for width in (1440, 390):
        public_page.set_viewport_size({'width': width, 'height': 1000})
        public_page.goto(base + '/portal')
        public_page.get_by_role('heading', name='Welcome back.', exact=True).wait_for()
        assert public_page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        public_page.screenshot(path=str(output / f'portal-{width}.png'), full_page=True, animations='disabled')
    public.close()
    page.goto(base + '/dashboard/reports')
    page.get_by_text('Export report', exact=True).click()
    assert page.get_by_role('link', name='Export CSV', exact=True).is_visible()
    assert page.get_by_role('link', name='Export Excel', exact=True).is_visible()
    assert page.get_by_role('link', name='Export PDF', exact=True).is_visible()
    page.get_by_text('More filters', exact=True).click()
    assert page.locator('select[name=version_id]').is_visible()
    page.goto(base + '/dashboard/data')
    page.get_by_text('Export workbook', exact=True).click()
    assert page.get_by_role('link', name='Original format: questions', exact=True).is_visible()
    assert page.get_by_role('link', name='Original format: questions & answers', exact=True).is_visible()
    # Leave shared auth checks on a desktop overview with an accessible Sign out.
    page.goto(base + '/dashboard')
    page.locator('#content .stats').wait_for()
    print('PASS: single Department modal with Type then Name, validation/cancel/retry, university/ministry CRUD, optional category, shared home/admin blue, sign-in responsiveness and export menus', flush=True)
