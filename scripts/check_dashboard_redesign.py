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
from playwright.sync_api import sync_playwright
import uvicorn

def main():
    output=Path('/tmp/dedc-redesign-review')
    phase='before' if '--before' in sys.argv else 'after'
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
                routes=['','/survey-builder','/forms','/departments','/reports','/users','/data','/data?tab=answers','/settings','/audit',f'/forms/{draft_id}',f'/forms/{form_id}/preview']
                def ready():
                    page.locator('#content .skeleton').wait_for(state='detached')
                    page.locator('#content[aria-busy=true]').wait_for(state='detached')
                    if page.locator('body').get_attribute('data-page') == 'survey-builder':
                        page.locator('#years-table tbody tr').first.wait_for()
                    page.evaluate('document.fonts.ready')
                for width in (() if '--interactions' in sys.argv else ((1440,390) if phase=='before' else (1440,1024,768,390))):
                    page.set_viewport_size({'width':width,'height':1000})
                    for index,route in enumerate(routes):
                        page.goto(base+'/dashboard'+route);ready()
                        assert page.locator('#content > .notice.error').count()==0,(width,route,page.locator('#content').inner_text())
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,route,'overflow')
                        page.screenshot(path=str(output/phase/f'{index:02}-{width}.png'),full_page=True,animations='disabled')
                    print(f'{phase}: all routes at {width}px',flush=True)
                if phase=='after':
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
