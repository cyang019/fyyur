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
    shows = db.relationship("Show", backref="venues")

    def __repr__(self):
      return f'<Venue {self.id} {self.name}>'


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
    shows = db.relationship("Show", backref="artists")

    def __repr__(self):
      return f'<Artist {self.id} {self.name}>'


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
