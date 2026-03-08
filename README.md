Frogwatch
=========

This app downloads Frogwatch observations from Fieldscope into a local database, and
provides a dashboard for visualizing those observations.

While it can download Fieldscope data for any locations, the dashboard just
presents data for in South Mountain Reservation, Essex County, NJ.

The dashboard can run locally as a Jupyter notebook, or as a web app on Heroku.


Installation
------------
These instructions assume that you have python 3.9, postgres 9.5 (or later) and the
heroku cli tool installed, already.

Initialize the virtual env with the python dependencies for the project, using the
following command

     uv sync


Database
--------
Set the DATABASE_URL parameter in frogwatch/settings.py to point to the local copy
of the frogwatch database.  For me, this is usually either a Postgres database or an
SQLite database

When deployed on Heroku, a DATABASE_URL environment variable will automatically be
defined to point to the production db.

#### Postgres
For a local Postgres db, set the database URL as follows. (the username, password and
database name here are just examples.)

     DATABASE_URL = "postgres://{user}:{passwd}@{host}:{port}/{database}".format(
        user="frogger", passwd="s3cre7", host="127.0.0.1", port="5432", database="frogwatch")

#### SQLite


#### Heroku



FieldScope Data
---------------

3. Initialize the database.  If you have an existing Postgres db on
   Heroku, you can clone it locally using the command

     heroku pg:pull <heroku-db-id> frogwatch --app frogwatch

   Otherwise, create a new local database with the command

     createdb frogwatch

4. You can now start up a local copy of the site using the commands

     export BOKEH_ALLOW_WS_ORIGIN=0.0.0.0:5000
     heroku local

7. Vist the local site at http://localhost:5000/ or http://localhost:5000/admin


Working with Heroku
-------------------

Install heroku cli

heroku pg:info

heroku pg:reset

heroku pg:push

heroku pg:pull

heroku local


Loading Data from Fieldscope
----------------------------

1. Create local database (if necessary)

     createdb frogwatch

2. Load data from Fieldscope into local database

     frogwatch --hartshorne  --db

3. Delete stations and observers from other projects.
   (This is necessary to keep the size of the database below 10,000 rows,
   at which point we'd have to start paying heroku for the database.)

     psql> \c frogwatch
     psql> delete from persons where fs_id not in (select distinct observer_id from observations);
     psql> delete from stations where fs_id not in (select distinct station_id from observations);

4. Replace the heroku database with a clone of our local database

     heroku pg:reset postgresql-closed-16712
     heroku pg:push frogwatch postgresql-closed-16712 --app frogwatch


