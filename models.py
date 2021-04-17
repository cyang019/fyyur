from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#
class VenueGenre(db.Model):
  __tablename__ = 'venue_genre'
  __table_args__ = (
    {'extend_existing': True}
  )

  id = db.Column(db.Integer, primary_key=True, nullable=False)
  category = db.Column(db.String, nullable=False)
  venue_id = db.Column(db.Integer, db.ForeignKey('venues.id', ondelete="CASCADE"))
  # venue_name = db.Column(db.String, db.ForeignKey('venues.name'))


class ArtistGenre(db.Model):
  __tablename__ = 'artist_genre'
  __table_args__ = (
    {'extend_existing': True}
  )
  
  id = db.Column(db.Integer, primary_key=True, nullable=False)
  category = db.Column(db.String, nullable=False)
  artist_id = db.Column(db.Integer, db.ForeignKey('artists.id', ondelete="CASCADE"))
  # artist_name = db.Column(db.String, db.ForeignKey('artists.name'))


class Venue(db.Model):
    __tablename__ = 'venues'
    __table_args__ = (
      {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    name = db.Column(db.String, nullable=False, unique=True)
    # genres = db.Column(db.String)
    genres = db.relationship('VenueGenre', backref='venues', lazy=True, cascade="all,delete,delete-orphan")
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website = db.Column(db.String)
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, nullable=False)
    seeking_description = db.Column(db.String, nullable=True)
    image_link = db.Column(db.String(500))
    created_date = db.Column(db.DateTime(timezone=True), nullable=True, default=datetime.now(timezone.utc))
    shows = db.relationship("Show", backref="venues")

    def __repr__(self):
      return f'<Venue {self.id} {self.name}>'
    
    def to_dictionary(self):
      fmt = '%Y-%m-%dT%H:%M:%S.%f'
      data = {
        'id': self.id,
        'name': self.name,
        'genres': [item.category for item in self.genres],
        'address': self.address,
        'city': self.city,
        'state': self.state,
        'phone': self.phone,
        'website': self.website,
        'facebook_link': self.facebook_link,
        'seeking_talent': self.seeking_talent,
        'seeking_description': self.seeking_description,
        'image_link': self.image_link,
        'created_date': self.created_date.strftime(fmt)[:-3] + 'Z',
        'past_shows': [],
        'upcoming_shows': [],
        'past_shows_count': 0,
        'upcoming_shows_count': 0
      }
      return data


class Artist(db.Model):
    __tablename__ = 'artists'
    __table_args__ = (
      {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    name = db.Column(db.String, nullable=False, unique=True)
    # genres = db.Column(db.String(120))
    genres = db.relationship('ArtistGenre', backref='artists', lazy=True, cascade="all,delete,delete-orphan")
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website = db.Column(db.String)
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, nullable=False)
    seeking_description = db.Column(db.String, nullable=True)
    image_link = db.Column(db.String(500))
    created_date = db.Column(db.DateTime(timezone=True), nullable=True, default=datetime.now(timezone.utc))
    shows = db.relationship("Show", backref="artists")

    def __repr__(self):
      return f'<Artist {self.id} {self.name}>'

    def to_dictionary(self):
      fmt = '%Y-%m-%dT%H:%M:%S.%f'
      data = {
        'id': self.id,
        'name': self.name,
        'genres': [item.category for item in self.genres],
        'city': self.city,
        'state': self.state,
        'phone': self.phone,
        'website': self.website,
        'facebook_link': self.facebook_link,
        'seeking_venue': self.seeking_venue,
        'seeking_description': self.seeking_description,
        'image_link': self.image_link,
        'created_date': self.created_date.strftime(fmt)[:-3] + 'Z',
        'past_shows': [],
        'upcoming_shows': [],
        'past_shows_count': 0,
        'upcoming_shows_count': 0
      }
      return data


class Show(db.Model):
  __tablename__ = 'shows'
  __table_args__ = (
    {'extend_existing': True},
  )
  id = db.Column(db.Integer, primary_key=True)
  start_time = db.Column(db.DateTime(timezone=True), nullable=True, 
                         default=datetime.now(timezone.utc))
  venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=False)
  artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
  
  def __repr__(self):
    return f'<Show {self.id} {self.venue_id} {self.artist_id}>'


  def to_dictionary(self, category=None):
    fmt = '%Y-%m-%dT%H:%M:%S.%f'
    data = {
      'artist_id': self.artist_id,
      'start_time': self.start_time.strftime(fmt)[:-3] + 'Z'
    }
    if category is None:
      pass
    elif category == 'artist':
      artist = Artist.query.get(self.artist_id)
      data['artist_name'] = artist.name
      data['artist_image_link'] = artist.image_link
    elif category == 'venue':
      venue = Venue.query.get(self.venue_id)
      data['venue_name'] = venue.name
      data['venue_image_link'] = venue.image_link
    else:
      raise NotImplementedError
    return data
