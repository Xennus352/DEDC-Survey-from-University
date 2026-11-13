"""Review all dashboard routes and workflows against a temporary ten-table database.

Run: uv run --with playwright python scripts/check_dashboard_redesign.py
Add --before to record a baseline, or --interactions to skip the viewport matrix.
Screenshots are saved under /tmp/dedc-redesign-review. No configured DB is used.
"""
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright, expect
import uvicorn

def main():
    output=Path('/tmp/dedc-redesign-review')
    phase='before' if '--before' in sys.argv else 'after'
    settings_only='--settings-only' in sys.argv
    overview_only='--overview-only' in sys.argv
    (output/phase).mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dedc-redesign-') as folder:
        os.environ.update(DATABASE_URL=f'sqlite:///{folder}/test.db', PRIVATE_STORAGE_DIR=f'{folder}/private',PORTAL_COOKIE_SECURE='false')
        from app.database import engine,SessionLocal
        from app.storage.existing import metadata
        from app.models.user import User,UserRole
        from app.crud.admin_session import create_session
        from app.portal_auth import hash_password
        from app.services import forms
        from app.schemas.forms import CreateForm,DraftInput,SubmissionInput
        from app.main import app
        metadata.create_all(engine)
        with engine.begin() as c:
            c.execute(metadata.tables['university'].insert(),[{'uniId':1,'uniType':'Computer studies','uniName':'University of Computer Studies, Taungoo'},{'uniId':2,'uniType':'Public','uniName':'ရန်ကုန် ကွန်ပျူတာတက္ကသိုလ်'}])
            c.execute(metadata.tables['ministry'].insert(),[{'ministryId':1,'ministryName':'Ministry of Science and Technology'}])
        with SessionLocal() as db:
            db.add_all([UserRole(id=1,name='Admin'),UserRole(id=2,name='University')]);db.flush()
            db.add_all([User(id=1,username='captain',password_hash=hash_password('review-password'),role_id=1,university_id=1),User(id=2,username='taungoo-research',password_hash='unused',role_id=2,university_id=2)]);db.commit()
            form=forms.create_form(db,CreateForm(title='University digital development survey',audience='university'),1)
            version=forms.save_draft(db,form.id,form.versions[0].id,DraftInput(title=form.title,reporting_start='2021-01-01',reporting_end='2026-03-31',sections=[{'title':'Digital infrastructure','questions':[{'key':'labs','title':'How many computer laboratories are available?','kind':'number','required':True},{'key':'network','title':'Is campus-wide internet available?','kind':'yes_no'}]},{'title':'Teaching and research','questions':[{'key':'details','title':'Describe your digital learning initiatives','kind':'long_text'}]}]),1)
            forms.publish(db,form.id,version.id,version.revision,1)
            forms.submit(db,form.id,SubmissionInput(reporting_start='2021-01-01',reporting_end='2026-03-31',answers={'labs':8,'network':True,'details':'Digital learning materials and research facilities'}),1)
            form_id=form.id
            draft=forms.create_form(db,CreateForm(title='Ministry services and digital readiness',audience='ministry'),1)
            draft_id=draft.id
            token=create_session(db,1)
        if settings_only:
            with SessionLocal() as db:
                db.add_all([User(username=f'review-admin-{i:02}',password_hash='unused',role_id=1)
                            for i in range(27)])
                db.commit()
        if '--private-metadata' in sys.argv:
            from app.storage.compact import CompactSession
            from app.storage.metadata_migration import migrate
            from app.config import settings
            with CompactSession(engine, settings.PRIVATE_STORAGE_DIR, 'maintenance') as db:
                migrate(db.native, db.files, engine)
            settings.METADATA_STORAGE = 'private'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning'))
        worker=threading.Thread(target=server.run,daemon=True);worker.start()
        deadline = time.monotonic() + 10
        while not server.started:
            if not worker.is_alive() or time.monotonic() > deadline:
                raise RuntimeError('Temporary dashboard server failed to start')
            time.sleep(.05)
        try:
            with sync_playwright() as p:
                browser=p.firefox.launch(headless=True)
                context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                context.add_cookies([{'name':'dedc_portal_session','value':token,'url':base}])
                context.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
                page=context.new_page();page.set_default_timeout(12000)
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                routes=['/settings'] if settings_only else [''] if overview_only else ['', '/forms','/departments','/ministries','/reports','/users','/data','/data?tab=answers','/settings','/audit',f'/forms/{draft_id}',f'/forms/{form_id}/preview']
                def ready():
                    page.locator('#content .skeleton').wait_for(state='detached')
                    page.locator('#content[aria-busy=true]').wait_for(state='detached')
                    page.evaluate('document.fonts.ready')
                for width in (() if '--interactions' in sys.argv else ((1440,390) if phase=='before' else (1440,1024,768,390))):
                    page.set_viewport_size({'width':width,'height':1000})
                    for index,route in enumerate(routes):
                        page.goto(base+'/dashboard'+route);ready()
                        assert page.locator('#content > .notice.error').count()==0,(width,route,page.locator('#content').inner_text())
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,route,'overflow')
                        page.screenshot(path=str(output/phase/f'{index:02}-{width}.png'),full_page=True,animations='disabled')
                        if overview_only:
                            expect(page.locator('.overview-metrics .overview-metric')).to_have_count(4)
                            assert page.locator('.overview-metrics .stat-cta').count()==0
                            row_count=page.locator('.overview-metrics .overview-metric').evaluate_all('(cards) => new Set(cards.map((card) => Math.round(card.getBoundingClientRect().top))).size')
                            assert row_count==(4 if width<640 else 2 if width<1024 else 1),(width,row_count)
                        if settings_only:
                            assert page.locator('.settings-row:visible').count()==1
                            for tab in ('administrators','appearance'):
                                page.locator(f'[data-settings-tab="{tab}"]').click()
                                assert page.locator('.settings-row:visible').count()==1
                                assert page.locator(f'#{tab}:visible').count()==1
                                page.screenshot(path=str(output/phase/f'settings-{tab}-{width}.png'),full_page=True,animations='disabled')
                    print(f'{phase}: all routes at {width}px',flush=True)
                if overview_only:
                    expect(page.locator('.overview-metrics .overview-metric strong')).to_have_text(['3','2','2','1'])
                    assert page.locator('.overview-metrics .overview-metric').evaluate_all('(cards) => cards.map((card) => card.getAttribute("href"))')==['/dashboard/forms?org_type=university','/dashboard/forms?org_type=ministry','/dashboard/departments','/dashboard/ministries']
                    print('PASS: overview metrics, links, and responsive layout',flush=True)
                    return
                if settings_only:
                    for route in ('/', '/portal', '/dashboard'):
                        response=page.goto(base+route)
                        assert response.status == 200,(route,response.status)
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(route,'overflow')
                    page.goto(base+'/dashboard/settings');ready()
                    page.locator('[data-settings-tab="administrators"]').click()
                    expect(page.locator('#administrators tbody tr')).to_have_count(10)
                    page.locator('.pagination__page[data-pagination="3"]').click();ready()
                    expect(page.locator('#administrators tbody tr')).to_have_count(8)
                    page.get_by_role('button',name='စီမံခန့်ခွဲသူ ထည့်ရန်').click()
                    assert page.locator('#administrator-form input[name=is_active]').count()==0
                    page.locator('#administrator-form input[name=username]').fill('review-new-admin')
                    page.locator('#administrator-form input[name=password]').fill('review-password-123')
                    page.locator('#administrator-form button[type=submit]').click()
                    page.locator('#workspace-dialog').wait_for(state='hidden')
                    page.locator('#admin-search').fill('review-new-admin')
                    page.locator('.settings-search button[type=submit]').click();ready()
                    expect(page.locator('#administrators tbody tr')).to_have_count(1)
                    page.locator('.settings-mobile-list [data-edit-admin]').click()
                    page.locator('#administrator-form input[name=username]').fill('review-renamed-admin')
                    page.locator('#administrator-form button[type=submit]').click()
                    page.locator('#workspace-dialog').wait_for(state='hidden')
                    page.locator('#admin-search').fill('review-renamed-admin')
                    page.locator('.settings-search button[type=submit]').click();ready()
                    expect(page.locator('#administrators tbody')).to_contain_text('review-renamed-admin')
                    page.locator('.settings-mobile-list [data-delete-admin]').click()
                    page.locator('[data-confirm-delete]').click()
                    page.locator('#workspace-dialog').wait_for(state='hidden')
                    expect(page.locator('#administrators tbody tr')).to_have_count(0)
                    page.locator('[data-settings-tab="account"]').click()
                    page.locator('#password-form input[name=current_password]').fill('review-password')
                    page.locator('#password-form input[name=new_password]').fill('updated-review-password')
                    page.locator('#password-form input[name=confirm_password]').fill('updated-review-password')
                    page.locator('#password-form button[type=submit]').click()
                    expect(page.locator('#password-feedback')).to_have_attribute('data-state','success')
                    page.reload();ready()
                    assert page.locator('#account:visible').count()==1
                    page.goto(base+'/dashboard/users');ready()
                    page.locator('#add-user').click()
                    assert page.locator('#user-form input[name=is_active]').count()==0
                    page.locator('#workspace-dialog [data-close-dialog]').click()
                    page.goto(base+'/dashboard/settings#appearance');ready()
                    page.locator('label.settings-theme-option:has(input[value=dark])').click()
                    expect(page.locator('input[name=theme-setting][value=dark]')).to_be_checked()
                    assert page.evaluate('document.documentElement.dataset.theme')=='dark'
                    assert page.evaluate('localStorage.getItem("dedc-theme")')=='dark'
                    page.reload();ready()
                    expect(page.locator('input[name=theme-setting][value=dark]')).to_be_checked()
                    page.locator('[data-theme-toggle]').click()
                    expect(page.locator('input[name=theme-setting][value=light]')).to_be_checked()
                    assert page.evaluate('document.documentElement.dataset.theme')=='light'
                    page.locator('label.settings-theme-option:has(input[value=dark])').click()
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    page.evaluate('window.scrollTo(0, 0)')
                    page.screenshot(path=str(output/phase/'settings-dark-390.png'),full_page=True,animations='disabled')
                    print('PASS: settings pagination, administrator CRUD and own password change',flush=True)
                elif phase=='after':
                    try:
                        from dashboard_redesign_checks import check
                        check(page, context, base, ready, output)
                    except Exception:
                        page.screenshot(path=str(output/phase/'failure.png'),full_page=True)
                        print(page.locator('body').inner_text()[-4000:],flush=True)
                        raise
                if '--private-metadata' in sys.argv:
                    from app.storage.compact import envelope
                    from sqlalchemy import select
                    with SessionLocal() as db:
                        assert not any(envelope(row['description']) for row in db.native.execute(select(metadata.tables['questiontitle'])).mappings())
                    print('PASS: all browser writes kept questiontitle free of application metadata', flush=True)
                assert not errors,errors
                browser.close()
        finally:
            server.should_exit=True;worker.join(timeout=5)
    print('Review completed:',output/phase)


if __name__ == '__main__':
    main()
