#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import sys
import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db, VenueGenre, Venue, ArtistGenre, Artist, Show
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres@localhost:5432/fyyur'
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
  return render_template('pages/home.html')


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
    abort(500)
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
    abort(500)
  else:
    return redirect(url_for('show_venue', venue_id=venue_id))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  error = False
  data={}
  try:
    query = db.session.query(
      Venue, Artist, Show
    ).join(Show, Venue.id == Show.venue_id).join(Artist, Artist.id == Show.artist_id)
    results = query.filter(Venue.id == venue_id).all()
    if results is None or len(results) == 0:
      venue = Venue.query.get(venue_id)
    else:
      venue = results[0][0]
    data['id'] = venue.id
    data['name'] = venue.name
    data['genres'] = [item.category for item in venue.genres]
    data['address'] = venue.address
    data['city'] = venue.city
    data['state'] = venue.state
    data['phone'] = venue.phone
    data['website'] = venue.website
    data['facebook_link'] = venue.facebook_link
    data['seeking_talent'] = venue.seeking_talent
    if data['seeking_talent']:
      data['seeking_description'] = venue.seeking_description
    data['image_link'] = venue.image_link
    data['past_shows'] = []
    data['upcoming_shows'] = []
    data['past_shows_count'] = 0
    data['upcoming_shows_count'] = 0
    fmt = '%Y-%m-%dT%H:%M:%S.%f'
    current_time = datetime.now(timezone.utc)
    for _, artist, show in results:
      temp = {
        'artist_id': show.artist_id,
        'artist_name': artist.name,
        'artist_image_link': artist.image_link,
        'start_time': show.start_time.strftime(fmt)[:-3] + 'Z'
      }
      if show.start_time > current_time:
        data['upcoming_shows_count'] += 1
        data['upcoming_shows'].append(temp)
      else:
        data['past_shows_count'] += 1
        data['past_shows'].append(temp)
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
    abort(500)

  # shows the venue page with the given venue_id
  # DONE: replace with real venue data from the venues table, using venue_id

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False
  venue_id = None
  try:
    venue = Venue(
      name=request.form['name'],
      city=request.form['city'],
      state=request.form['state'],
      address=request.form['address'],
      phone=request.form['phone'],
      website=request.form['website_link'],
      facebook_link=request.form['facebook_link'],
      image_link=request.form['image_link'],
      seeking_talent = False
    )
    if 'seeking_talent' in request.form:
      venue.seeking_talent = request.form['seeking_talent'] == 'y'
    if venue.seeking_talent is True:
      venue.seeking_description = request.form['seeking_description']
    for genre_item in request.form.getlist('genres'):
      temp_genre = VenueGenre(category=genre_item)
      venue.genres.append(temp_genre)
    db.session.add(venue)
    # venue_id = venue.id
    db.session.commit()
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
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
    return redirect(url_for('show_venue_by_name', venue_name=request.form['name']))
  else:
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
    abort(500)

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
  # data=[{
  #   "id": 4,
  #   "name": "Guns N Petals",
  # }, {
  #   "id": 5,
  #   "name": "Matt Quevedo",
  # }, {
  #   "id": 6,
  #   "name": "The Wild Sax Band",
  # }]
  if not error:
    return render_template('pages/artists.html', artists=data)
  else:
    abort(500)

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
    abort(500)
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
    abort(500)
  else:
    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  error = False
  data={}
  try:
    query = db.session.query(
      Artist, Venue, Show
    ).join(Show, Show.artist_id == Artist.id).join(Venue, Venue.id == Show.venue_id)
    results = query.filter(Artist.id == artist_id).all()
    if results is None or len(results) == 0:
      artist = Artist.query.get(artist_id)
    else:
      artist = results[0][0]
    data['id'] = artist.id
    data['name'] = artist.name
    data['genres'] = [item.category for item in artist.genres]
    data['city'] = artist.city
    data['state'] = artist.state
    data['phone'] = artist.phone
    data['website'] = artist.website
    data['facebook_link'] = artist.facebook_link
    data['seeking_talent'] = artist.seeking_venue
    if data['seeking_talent']:
      data['seeking_description'] = artist.seeking_description
    data['image_link'] = artist.image_link
    data['past_shows'] = []
    data['upcoming_shows'] = []
    data['past_shows_count'] = 0
    data['upcoming_shows_count'] = 0
    fmt = '%Y-%m-%dT%H:%M:%S.%f'
    current_time = datetime.now(timezone.utc)
    for _, venue, show in results:
      temp = {
        'venue_id': show.venue_id,
        'venue_name': venue.name,
        'venue_image_link': venue.image_link,
        'start_time': show.start_time.strftime(fmt)[:-3] + 'Z'
      }
      if show.start_time > current_time:
        data['upcoming_shows_count'] += 1
        data['upcoming_shows'].append(temp)
      else:
        data['past_shows_count'] += 1
        data['past_shows'].append(temp)
  except Exception as e:
    error = True
    print(f'error showing venue for {artist_id}.')
    print(e)
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    return render_template('pages/show_artist.html', artist=data)
  else:
    abort(500)
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
    artist = {
      "id": artist_db.id,
      "name": artist_db.name,
      "genres": [item.category for item in artist_db.genres],
      "city": artist_db.city,
      "state": artist_db.state,
      "phone": artist_db.phone,
      "website": artist_db.website,
      "facebook_link": artist_db.facebook_link,
      "seeking_venue": artist_db.seeking_venue,
      "seeking_description": artist_db.seeking_description,
      "image_link": artist_db.image_link
    }
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
  # print(request.form)
  try:
    artist = Artist.query.get(artist_id)
    artist.name = request.form['name']
    ArtistGenre.query.filter(ArtistGenre.artist_id == artist.id).delete()
    for genre in request.form.getlist('genres'):
      artist.genres.append(ArtistGenre(category=genre))
    artist.city = request.form['city']
    artist.state = request.form['state']
    artist.phone = request.form['phone']
    artist.website = request.form['website_link']
    artist.facebook_link = request.form['facebook_link']
    artist.image_link = request.form['image_link']
    if 'seeking_venue' in request.form:
      artist.seeking_venue = request.form['seeking_venue'] == 'y'
    else:
      artist.seeking_venue = False
    if artist.seeking_venue:
      artist.seeking_description = request.form['seeking_description']
    else:
      artist.seeking_description = ''
    db.session.commit()
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
    abort(500)

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = None
  venue_dict = {}
  try:
    venue = Venue.query.get(venue_id)
    venue_dict = {
      "id": venue.id,
      "name": venue.name,
      "genres": [item.category for item in venue.genres],
      "address": venue.address,
      "city": venue.city,
      "state": venue.state,
      "phone": venue.phone,
      "website": venue.website,
      "facebook_link": venue.facebook_link,
      "seeking_talent": venue.seeking_talent,
      "seeking_description": venue.seeking_description,
      "image_link": venue.image_link
    }
  except Exception as e:
    print(f'error editing venue {venue_id}')
    print(e)
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()
  if venue is None:
    form = VenueForm()
  else:
    form = VenueForm(obj=venue)
  
  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue_dict)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  error = False
  try:
    venue = Venue.query.get(venue_id)
    venue.name = request.form['name']
    VenueGenre.query.filter(VenueGenre.venue_id == venue_id).delete()
    for genre in request.form.getlist('genres'):
      venue.genres.append(VenueGenre(category=genre))
    venue.address = request.form['address']
    venue.city = request.form['city']
    venue.state = request.form['state']
    venue.phone = request.form['phone']
    venue.website = request.form['website_link']
    venue.facebook_link = request.form['facebook_link']
    venue.image_link = request.form['image_link']
    if 'seeking_talent' in request.form:
      venue.seeking_talent = request.form['seeking_talent'] == 'y'
    else:
      venue.seeking_talent = False
    if venue.seeking_talent:
      venue.seeking_description = request.form['seeking_description']
    else:
      venue.seeking_description = ''
    db.session.commit()
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
    abort(500)

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  error = False
  try:
    artist = Artist(
      name=request.form['name'],
      city=request.form['city'],
      state=request.form['state'],
      phone=request.form['phone'],
      website=request.form['website_link'],
      facebook_link=request.form['facebook_link'],
      image_link=request.form['image_link'],
      seeking_venue = False
    )
    if 'seeking_venue' in request.form:
      artist.seeking_venue = request.form['seeking_venue'] == 'y'
    if artist.seeking_venue is True:
      artist.seeking_description = request.form['seeking_description']
    for genre_item in request.form.getlist('genres'):
      temp_genre = ArtistGenre(category=genre_item)
      artist.genres.append(temp_genre)
    db.session.add(artist)
    # artist_id = artist.id
    db.session.commit()
  except Exception as e:
    error = True
    print(f'error inserting artist for {request.form["name"]}.')
    print(f'error message: \n{e}')
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
    return redirect(url_for('show_artist_by_name', artist_name=request.form['name']))
  else:
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
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
  try:
    pattern = r'%Y-%m-%d %H:%M:%S'
    show = Show(
      id = show_id(),
      artist_id = request.form['artist_id'],
      venue_id = request.form['venue_id'],
      start_time = datetime.strptime(request.form['start_time'], pattern)
    )
    db.session.add(show)
    db.session.commit()
  except Exception as e:
    print(f'create show error: {e}')
    error = True
  finally:
    db.session.close()


  if not error:
    flash('Show was successfully listed!')
    return redirect(url_for('shows'))
  else:
    flash('An error occurred. Show could not be listed.')
    abort(500)
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead

  # on successful db insert, flash success
  
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Show could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  # return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

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
