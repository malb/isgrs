Most steps are pretty self explanatory.

### User Management ###

I didn't implement a UI for user management. You can add new users by calling

    from isgrs.factory import make_session, create_app, db, create_user

    session = make_session()
    app = create_app()
    app.app_context().push()

    create_user(app, firstname="First", lastname="Last",
                email='em@i.l',
                password='password', lead=True)
    db.session.commit()

Users have two attributes (roles are pretty much ignored, the framework we're using requires them):

- `active` means a user can log in and is considered an active administrator/coordinator of the seminars. Announcement emails are signed on behalf of all `active` users.

- `lead` there should at any one time only be one active user/admin who is the lead user, this is now actively enforced at the moment, though. The lead users is, for example, assigned as the default minder when bulk adding new seminars.

The current active users are
{% for user in active_users %}
- {{user.firstname}} {{user.lastname}} [{{user.email}}](mailto:{{user.email}}) {% if user.lead %}, seminar lead{% endif %}
{% endfor %}

To change one of those attributes you can run

    session = make_session()
    app = create_app()
    app.app_context().push()

    from isgrs.models import User
    User.query.filter(User.email="em@i.l").one().lead = True
    db.session.commit()

and so on.

### Announcements ###

All admin tasks require to be logged in and should also require two steps to be completed (to prevent XSRF attacks). The exception to this rule are

- {{config['FRONTEND_DOMAIN']}}{{url_for('.json_announce', token=current_user.announce_token, eventid='next')}} and 

- {{config['FRONTEND_DOMAIN']}}{{url_for('.announce', token=current_user.announce_token, eventid='next')}}

They both directly send out the announcement without waiting for user feedback. Additionally, the json variant does not use Flask-Security's login login mechanism for authentication but instead a static token (i.e. the link above requires **no** authentication and specific to you). This enables to script sending out the next announcement without having to open a browser, type in a URL, login, click a few times.

### Local Development & Testing ###

1. Create and activate a Python virtual environment
2. Run ``pip install -r requirements.txt``
3. Run ``flask db upgrade``
4. Edit ``config.py`` with local settings
5. Run ``flask run``

