#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import sys
import json
import dateutil.parser
import babel
from flask import (
  Flask,
  render_template,
  request,
  Response,
  flash,
  redirect,
  url_for,
  abort
)
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import (
  db,
  VenueGenre,
  Venue,
  ArtistGenre,
  Artist,
  Show
)
import logging
from logging import Formatter, FileHandler
from flask_wtf import FlaskForm as Form
from forms import *
from datetime import datetime, timezone
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
# connect to a local postgresql database
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres@localhost:5432/fyyur'
# avoid warning message
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db, compare_type=True)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  venues = Venue.query.order_by(db.desc(Venue.created_date)).limit(10).all()
  artists = Artist.query.order_by(db.desc(Artist.created_date)).limit(10).all()
  return render_template('pages/home.html', venues=venues, artists=artists)


#  Venues
#  ----------------------------------------------------------------
def convert_str_to_datetime(datetime_str):
  pattern = r'%Y-%m-%dT%H:%M:%S.%fZ'
  date_time_obj = datetime.strptime(datetime_str, pattern)
  return date_time_obj


def search_future_shows(item_id, category=None):
  current_time = datetime.now(timezone.utc)
  shows = None
  if category is None:
    raise NotImplementedError
    # shows = Show.query.filter(Show.id == item_id, Show.start_time > current_time).all()
  else:
    if category == 'venue':
      shows = Show.query.filter(Show.venue_id==item_id, Show.start_time > current_time).all()
    elif category == 'artist':
      shows = Show.query.filter(Show.artist_id==item_id, Show.start_time > current_time).all()
    else:
      raise NotImplementedError
  return shows


def count_future_shows(item_id, category=None):
  shows = search_future_shows(item_id, category=category)
  count = 0
  if shows is not None and hasattr(shows, '__len__'):
    count = len(shows)
  return count


def search_past_shows(item_id, category=None):
  current_time = datetime.now(timezone.utc)
  shows = None
  if category is None:
    raise NotImplementedError
    # shows = Show.query.filter(Show.id == item_id, Show.start_time < current_time).all()
  else:
    if category == 'venue':
      shows = Show.query.filter(Show.venue_id==item_id, Show.start_time < current_time).all()
    elif category == 'artist':
      shows = Show.query.filter(Show.artist_id==item_id, Show.start_time < current_time).all()
    else:
      raise NotImplementedError
  return shows


def count_past_shows(item_id, category=None):
  shows = search_past_shows(item_id, category=category)
  count = 0
  if shows is not None and hasattr(shows, '__len__'):
    count = len(shows)
  return count


@app.route('/venues')
def venues():
  error = False
  data = []
  try:
    venues = Venue.query.all()
    locations = []
    for venue in venues:
      location = (venue.city, venue.state)
      if location not in locations:
        temp = {
          "city": venue.city,
          "state": venue.state,
          "venues": []
        }
        data.append(temp)
        locations.append(location)
      idx = locations.index(location)
      venue_info = {
        "id": venue.id,
        "name": venue.name,
        "num_upcoming_shows": count_future_shows(venue.id, 'venue')
      }
      data[idx]['venues'].append(venue_info)
  except Exception as e:
    db.session.rollback()
    print(f'[error] retrieving venues.')
    print(sys.exc_info())
  finally:
    db.session.close()

  # # TODO: replace with real venues data.
  # #       num_shows should be aggregated based on number of upcoming shows per venue.
  if not error:
    return render_template('pages/venues.html', areas=data)
  else:
    abort(500)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  print('process post request for serach_venues...')
  error = False
  response = {}
  try:
    search_term = request.form.get('search_term', '')
    print(f'search_term: {search_term}')
    query = db.session.query(
      Venue.id,
      Venue.name,
      Show.start_time
    ).join(Show, Show.venue_id == Venue.id)
    current_time = datetime.now(timezone.utc)
    data = query.filter(Venue.name.ilike(f'%{search_term}%')).all()
    if data is not None:
      response["data"] = []
      key_locations = {}
      for item in data:
        if item[0] in key_locations:
          key_id = item[0]
        else:
          temp = {
            'id': item[0],
            'name': item[1],
            'num_upcoming_shows': 0
          }
          key_locations[item[0]] = len(response["data"])
          response['data'].append(temp)
        if item[2] > current_time:
          response["data"][key_locations[item[0]]]["num_upcoming_shows"] += 1
      response["count"] = len(key_locations)
  except Exception as e:
    db.session.rollback()
    error = True
    print(f'error in search_venues(): {e}')
    print(sys.exc_info())
  finally:
    db.session.close()
  
  if not error:
    return render_template('pages/search_venues.html', 
    results=response, 
    search_term=search_term)
  else:
    abort(400)
  # TODO: implement search on venues with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"


@app.route('/venues/<venue_name>')
def show_venue_by_name(venue_name):
  venue_id = None
  try:
    venue_id = db.session.query(Venue.id).filter(Venue.name == venue_name).scalar()
  except Exception as e:
    print(e)
    print(sys.exc_info())
  finally:
    db.session.close()
  
  if venue_id is None:
    abort(404)
  else:
    return redirect(url_for('show_venue', venue_id=venue_id))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  error = False
  data={}
  try:
    venue = Venue.query.get(venue_id)
    current_time = datetime.now(timezone.utc)
    past_shows = list(filter(lambda x: x.start_time < current_time, venue.shows))
    upcoming_shows = list(filter(lambda x: x.start_time >= current_time, venue.shows))
    
    past_shows = list(map(lambda x: x.to_dictionary('artist'), past_shows))
    upcoming_shows = list(map(lambda x: x.to_dictionary('artist'), upcoming_shows))
    
    data = venue.to_dictionary()
    data['past_shows'] = past_shows
    data['past_shows_count'] = len(past_shows)

    data['upcoming_shows'] = upcoming_shows
    data['upcoming_shows_count'] = len(upcoming_shows)
  except Exception as e:
    error = True
    print(f'error showing venue for {venue_id}.')
    print(e)
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    return render_template('pages/show_venue.html', venue=data)
  else:
    abort(404)

  # shows the venue page with the given venue_id
  # DONE: replace with real venue data from the venues table, using venue_id

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm(request.form)
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False
  form = VenueForm(request.form)
  try:
    venue = Venue()
    if form.validate_on_submit():
      # Venue.genres is a list
      form.genres.data = [
        VenueGenre(category=item) for item in request.form.getlist('genres')
      ]
      form.populate_obj(venue)
      db.session.add(venue)
      db.session.commit()
      flash('Venue ' + request.form['name'] + ' was successfully listed!')
    else:
      error = True
      print(f'form errors: {form.errors}')
      for key, value in form.errors.items():
        flash(f'[{key}] {value}')
  except Exception as e:
    error = True
    print(f'error inserting venue for {request.form["name"]}.')
    print(f'error message: \n{e}')
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion

  # on successful db insert, flash success
  
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Venue ' + data.name + ' could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  if not error:
    return redirect(url_for('show_venue_by_name', venue_name=request.form['name']))
  else:
    return render_template('forms/new_venue.html', form=form)

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
  except Exception as e:
    error = True
    print(f'error deleting venue {venue_id}.')
    print(f'error message: \n{e}')
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  error = False
  data = []
  try:
    artists = Artist.query.all()
    locations = []
    for artist in artists:
      temp = {
        "id": artist.id,
        "name": artist.name
      }
      data.append(temp)
  except Exception as e:
    db.session.rollback()
    print(f'[error] retrieving venues.')
    print(sys.exc_info())
  finally:
    db.session.close()
  # TODO: replace with real data returned from querying the database
  if not error:
    return render_template('pages/artists.html', artists=data)
  else:
    abort(400)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  error = False
  response = {}
  try:
    search_term = request.form.get('search_term', '')
    print(f'search_term: {search_term}')
    query = db.session.query(
      Artist.id,
      Artist.name,
      Show.start_time
    ).join(Show, Show.artist_id == Artist.id)
    data = query.filter(Artist.name.ilike(f'%{search_term}%')).all()
    if data is not None:
      keys = []
      response["data"] = []
      current_time = datetime.now(timezone.utc)
      for artist_id, artist_name, show_start_time in data:
        idx = 0
        if artist_id not in keys:
          temp = {
            'id': artist_id,
            'name': artist_name,
            'num_upcoming_shows': 0
          }
          response['data'].append(temp)
          keys.append(artist_id)
        idx = keys.index(artist_id)
        if show_start_time > current_time:
          response["data"][idx]["num_upcoming_shows"] += 1
      response["count"] = len(keys)
  except Exception as e:
    db.session.rollback()
    error = True
    print(f'error in search_artists(): {e}')
    print(sys.exc_info())
  finally:
    db.session.close()
  
  if not error:
    return render_template('pages/search_artists.html', 
    results=response, 
    search_term=search_term)
  else:
    abort(404)
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".


@app.route('/artists/<artist_name>')
def show_artist_by_name(artist_name):
  artist_id = None
  try:
    artist_id = db.session.query(Artist.id).filter(Artist.name == artist_name).scalar()
  except Exception as e:
    print(e)
    print(sys.exc_info())
  finally:
    db.session.close()
  
  if artist_id is None:
    abort(404)
  else:
    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  error = False
  data={}
  try:
    artist = Artist.query.get(artist_id)
    current_time = datetime.now(timezone.utc)
    past_shows = list(filter(lambda x: x.start_time < current_time, artist.shows))
    upcoming_shows = list(filter(lambda x: x.start_time >= current_time, artist.shows))
    
    past_shows = list(map(lambda x: x.to_dictionary('venue'), past_shows))
    upcoming_shows = list(map(lambda x: x.to_dictionary('venue'), upcoming_shows))
    
    data = artist.to_dictionary()
    data['past_shows'] = past_shows
    data['past_shows_count'] = len(past_shows)

    data['upcoming_shows'] = upcoming_shows
    data['upcoming_shows_count'] = len(upcoming_shows)
  except Exception as e:
    error = True
    print(f'error showing artist for {artist_id}.')
    print(e)
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    return render_template('pages/show_artist.html', artist=data)
  else:
    abort(404)
  # shows the artist page with the given artist_id
  # TODO: replace with real artist data from the artist table, using artist_id

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  error = False
  form = None
  try:
    artist_db = Artist.query.get(artist_id)
    artist = artist_db.to_dictionary()
    form = ArtistForm(obj=artist_db)
  except Exception as e:
    error = True
    print(f'error editing artist {artist_id}.')
    print(request.form)
    print(e)
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()

  # TODO: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  error = False
  form, artist = None, None
  try:
    form = ArtistForm(request.form)
    if form.validate_on_submit():
      # Artist.genres is a list
      form.genres.data = [
        ArtistGenre(category=item) for item in request.form.getlist('genres')
      ]
      artist = Artist.query.get(artist_id)
      form.populate_obj(artist)
      db.session.commit()
    else:
      print(f'form errors: {form.errors}')
      for key, value in form.errors.items():
        flash(f'[{key}] {value}')
      error = True
      db.session.rollback()
      return redirect(url_for('edit_artist', artist_id=artist_id))
  except Exception as e:
    error = True
    print(f'error submitting artist {artist_id}.')
    print(request.form)
    print(e)
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  if not error:
    return redirect(url_for('show_artist', artist_id=artist_id))
  else:
    flash(f'Error editing artist {artist_id}')
    abort(400)

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = None
  venue_dict = {}
  error = False
  try:
    venue = Venue.query.get(venue_id)
    venue_dict = venue.to_dictionary()
    form = VenueForm(obj=venue)
  except Exception as e:
    print(f'error editing venue {venue_id}')
    print(e)
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()
  
  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue_dict)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  error = False
  try:
    form = VenueForm(request.form)
    if form.validate_on_submit():
      venue = Venue.query.get(venue_id)
      # modify genres so that it's compatible with children schema
      form.genres.data = [
        VenueGenre(category=item) for item in request.form.getlist('genres')
      ]
      form.populate_obj(venue)
      db.session.commit()
    else:
      error = True
      print(f'form errors: {form.errors}')
      for key, value in form.errors.items():
        flash(f'[{key}] {value}')
      db.session.rollback()
      return redirect(url_for('edit_venue', venue_id=venue_id))
  except Exception as e:
    error = True
    print(f'error submitting venue {venue_id}.')
    print(e)
    print(sys.exc_info())
    print(request.form)
    db.session.rollback()
  finally:
    db.session.close()
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  if not error:
    return redirect(url_for('show_venue', venue_id=venue_id))
  else:
    flash(f'error editing venue {venue_id}')
    abort(400)

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  form = ArtistForm(request.form)
  error = False
  try:
    if form.validate_on_submit():
      artist = Artist()
      # Artist.genres is a list
      form.genres.data = [
        ArtistGenre(category=item) for item in request.form.getlist('genres')
      ]
      form.populate_obj(artist)
      db.session.add(artist)
      db.session.commit()
      flash('Artist ' + request.form['name'] + ' was successfully listed!')
    else:
      error = True
      print(f'form errors: {form.errors}')
      for key, value in form.errors.items():
        flash(f'[{key}] {value}')
      return render_template('forms/new_artist.html', form=form)
  except ValueError as e:
    error = True
    print(f'Error creating artist: {e}')
    flash('Error creating artist.')
    db.session.rollback()
  except Exception as e:
    error = True
    print(f'Error creating artist: {e}')
    flash('Error creating artist.')
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    return redirect(url_for('show_artist_by_name', artist_name=request.form['name']))
  else:
    abort(500)
  # called upon submitting the new artist listing form
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion

  # on successful db insert, flash success
  
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
  # return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  data = []
  error = False
  try:
    query = db.session.query(
      Show.venue_id,
      Show.artist_id,
      Show.start_time,
      Venue.name,
      Artist.name,
      Artist.image_link
    ).join(Artist, Artist.id == Show.artist_id).join(Venue, Venue.id == Show.venue_id)
    shows = query.all()
    for show in shows:
      temp = {
        "venue_id": show[0],
        "artist_id": show[1],
        "start_time": show[2].strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
        "venue_name": show[3],
        "artist_name": show[4],
        "artist_image_link": show[5]
      }
      data.append(temp)
  except Exception as e:
    print(f'error showing shows: {e}')
    print(sys.exc_info())
    error = True
  finally:
    db.session.close()

  if not error:
    return render_template('pages/shows.html', shows=data)
  else:
    abort(500)
  # displays list of shows at /shows
  # TODO: replace with real venues data.

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

show_id_val = 10
def show_id():
  global show_id_val
  show_id_val += 1
  return show_id_val

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  error = False
  form = ShowForm(request.form)
  try:
    if form.validate_on_submit():
      show = Show()
      form.populate_obj(show)
      # pattern = r'%Y-%m-%d %H:%M:%S'
      db.session.add(show)
      db.session.commit()
      flash('Show was successfully listed!')
    else:
      error = True
      print(f'form errors: {form.errors}')
      for key, value in form.errors.items():
        flash(f'[{key}] {value}')
  except Exception as e:
    print(f'create show error: {e}')
    error = True
  finally:
    db.session.close()

  if not error:
    return redirect(url_for('shows'))
  else:
    return render_template('forms/new_show.html', form=form)
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead

  # on successful db insert, flash success
  
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Show could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  # return render_template('pages/home.html')

@app.errorhandler(400)
def not_found_error(error):
    return render_template('errors/400.html'), 400

@app.errorhandler(401)
def not_found_error(error):
    return render_template('errors/401.html'), 401

@app.errorhandler(403)
def not_found_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(405)
def not_found_error(error):
    return render_template('errors/405.html'), 405

@app.errorhandler(409)
def not_found_error(error):
    return render_template('errors/409.html'), 409

@app.errorhandler(422)
def not_found_error(error):
    return render_template('errors/422.html'), 422

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
