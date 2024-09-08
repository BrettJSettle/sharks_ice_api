"""Flask API for sharks app."""

import flask
import flask_cors
import flask_restful
from flask_restful import reqparse
import sharks_ice_lib as sil

app = flask.Flask(__name__)
cors = flask_cors.CORS(app, resources={r'*': {'origins': '*'}})
api = flask_restful.Api(app)

parser = reqparse.RequestParser()
parser.add_argument('reload')


def get_reload(default=False):
  args = parser.parse_args()
  return args.get('reload', default)


# Backend
class Main(flask_restful.Resource):

  def get(self):
    return flask.jsonify({
        'resources': [
            '/seasons',
            '/seasons/{seasonId}/divisions',
            '/seasons/{seasonId}/divisions/{divisionId}/conference/{conferenceId}',
            '/seasons/{seasonId}/teams/{teamId}',
            '/games/{gameId}',
            '/games',
        ]
    })


class Seasons(flask_restful.Resource):

  def get(self):
    try:
      return flask.jsonify({'seasons': sil.get_seasons()})
    except sil.Error as e:
      return flask.jsonify({'error': str(e)}), 500


class Divisions(flask_restful.Resource):

  def get(self, season_id: str):
    try:
      return flask.jsonify(
          {'divisions': sil.get_divisions(season_id=season_id)}
      )
    except sil.Error as e:
      return flask.jsonify({'error': str(e)})


class DivisionPlayers(flask_restful.Resource):

  def get(self, season_id: str, division_id: int, conference_id: str = '0'):
    try:
      players, goalies = sil.get_division_players(
          div_id=division_id,
          season_id=season_id,
          conference_id=conference_id,
          reload=get_reload(),
      )
      return flask.jsonify({'players': players, 'goalies': goalies})
    except sil.Error as e:
      return flask.jsonify({'error': str(e)})


class Team(flask_restful.Resource):

  def get(self, season_id: str, team_id: str):
    try:
      return flask.jsonify(
          sil.get_team(
              season_id=season_id, team_id=team_id, reload=get_reload()
          )
      )
    except sil.Error as e:
      return flask.jsonify({'error': str(e)})


class TeamName(flask_restful.Resource):

  def get(self, season_id: str):
    try:
      team_id = sil.get_team_id(
          season_id=season_id, team_name=flask.request.args.get('team')
      )
      if not team_id:
        return flask.jsonify(
            sil.get_all_teams(season_id=season_id, reload=get_reload())
        )
      return flask.jsonify(
          sil.get_team(
              season_id=season_id, team_id=team_id, reload=get_reload()
          )
      )
    except sil.Error as e:
      return flask.jsonify({'error': str(e)})


class Game(flask_restful.Resource):

  def get(self, game_id: str):
    try:
      return flask.jsonify(
          sil.get_game_stats(game_id=game_id, reload=get_reload())
      )
    except sil.Error as e:
      return flask.jsonify({'error': str(e)})


class Games(flask_restful.Resource):

  def get(self):
    try:
      return flask.jsonify(sil.get_games(reload=get_reload()))
    except sil.Error as e:
      return flask.jsonify({'error': str(e)})


class GamesApi(flask_restful.Resource):
  """API for reading games data."""

  def get(self):
    try:
      a = flask.request.args
      args = {
          'season_id': int(a['season_id']),
      }
      game_rows = sil.list_games(args)
      games = []
      for row in game_rows:
        info = row.get('info', {})
        games.append(
            dict(
                game_id=row.get('game_id', ''),
                away=info.get('away', ''),
                away=info.get('awayId', ''),
                home=info.get('home', ''),
                home=info.get('homeId', ''),
                awayGoals=info.get('awayGoals', ''),
                homeGoals=info.get('homeGoals', ''),
                date=info.get('date', ''),
                time=info.get('time', ''),
                league=info.get('league', ''),
                level=info.get('level', ''),
                rink=info.get('rink', ''),
            )
        )
      print('%d games' % len(games))
      return flask.jsonify({'games': games})
    except sil.Error as e:
      return flask.jsonify({'error': str(e)})


@app.errorhandler(404)
def page_not_found(e):
  # note that we set the 404 status explicitly
  return '404 Page Not Found\n%s' % e, 404


# Frontend
@app.route('/')
def index():
  return flask.render_template('index.html')


@app.route('/team')
def team():
  args = flask.request.args
  return flask.render_template('team.html', team_id=args.get('team_id', ''))


api.add_resource(Seasons, '/seasons')
api.add_resource(Divisions, '/seasons/<string:season_id>/divisions')
api.add_resource(
    DivisionPlayers,
    '/seasons/<string:season_id>/divisions/<int:division_id>/conference/<string:conference_id>',
    '/seasons/<string:season_id>/divisions/<int:division_id>',
)
api.add_resource(TeamName, '/seasons/<string:season_id>/teams')
api.add_resource(Game, '/games/<int:game_id>')
api.add_resource(Games, '/games')

api.add_resource(Main, '/api/')
api.add_resource(Team, '/api/seasons/<string:season_id>/teams/<int:team_id>')
api.add_resource(GamesApi, '/api/games')


if __name__ == '__main__':
  print('Running Flask app on port 5001')
  app.run(debug=True, host='0.0.0.0', port=5001)
