"""Flask API for sharks app."""

import flask
import flask_cors
import flask_restful
from flask_restful import reqparse
import sharks_ice_lib as sil
import database

app = flask.Flask(__name__)
cors = flask_cors.CORS(app, resources={r'*': {'origins': '*'}})
api = flask_restful.Api(app)

parser = reqparse.RequestParser()
parser.add_argument('reload')

def request_has_connection():
    return hasattr(flask.g, 'dbconn')

def get_request_connection():
    if not request_has_connection():
        flask.g.dbconn = database.Database()
        # Do something to make this connection transactional.
        # I'm not familiar enough with SQLite to know what that is.
    return flask.g.dbconn

@app.teardown_request
def close_db_connection(ex):
    if request_has_connection():
        conn = get_request_connection()
        # Rollback
        # Alternatively, you could automatically commit if ex is None
        # and rollback otherwise, but I question the wisdom 
        # of automatically committing.
        conn.close()


def get(variable="reload", default=False):
  args = flask.request.args
  return args.get(variable, default)


class Divisions(flask_restful.Resource):

  def get(self):
    try:
      db = get_request_connection()
      return flask.jsonify(
          db.list_season_divisions(season_id=66))
    except sil.Error as e:
      print(e)
      return flask.jsonify({'error': str(e)})


class Games(flask_restful.Resource):

  def get(self):
    team_ids = get('team_ids', [])
    team_ids = [int(i) for i in team_ids.split(',') if i]
    try:
      db = get_request_connection()
      current_season = db.get_current_season()
      print()
      return flask.jsonify(db.get_team_games(team_ids=team_ids, min_season=current_season))
    except sil.Error as e:
      return flask.jsonify({'error': str(e)})
    
class Teams(flask_restful.Resource):

  def get(self):
    team_ids = get('team_ids', [])
    team_ids = [int(i) for i in team_ids.split(',') if i]
    try:
      db = get_request_connection()
      current_season = db.get_current_season()
      return flask.jsonify(db.get_team_stats(team_ids=team_ids, season_id=current_season))
    except sil.Error as e:
      return flask.jsonify({'error': str(e)})



@app.errorhandler(404)
def page_not_found(e):
  # note that we set the 404 status explicitly
  return '404 Page Not Found\n%s' % e, 404


api.add_resource(Divisions, '/api/divisions')
api.add_resource(Games, '/api/games')
api.add_resource(Teams, '/api/teams')



if __name__ == '__main__':
  print('Running Flask app on port 5000')
  app.run(host='0.0.0.0', port=5000)
