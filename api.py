from flask import Flask, jsonify
import sharks_ice_lib as sil
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS

app = Flask(__name__)
api = Api(app)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

parser = reqparse.RequestParser()
parser.add_argument('reload')

def get_reload(default=False):
  args = parser.parse_args()
  return args.get('reload', default)

class Main(Resource):
  def get(self):
    return jsonify({
      'resources': [
        '/divisions',
        '/divisions/<div_id>/conference/<conf_id>',
        '/games/<id>',
        '/teams/<id>',
      ]
    })
class Division(Resource):
  def get(self):
    return jsonify(sil.get_divisions())

class DivisionPlayers(Resource):
  def get(self, division_id, conference_id):
    args = parser.parse_args()
    season_id = args.get('season_id', sil.get_current_season())
    return jsonify(sil.get_division_players(div_id=division_id, season_id=season_id, conference_id=conference_id, reload=get_reload()))

class Team(Resource):
  def get(self, team_id):
    return jsonify(sil.get_team(team_id=team_id, reload=get_reload()))

class Game(Resource):
  def get(self, game_id):
    return jsonify(sil.get_game_stats(game_id=game_id, reload=get_reload()))

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return 'Flask 404', 404

api.add_resource(Main, '/')
api.add_resource(Division, '/divisions')
api.add_resource(DivisionPlayers, '/divisions/<string:division_id>/conference/<string:conference_id>')
api.add_resource(Team, '/teams/<string:team_id>')
api.add_resource(Game, '/games/<string:game_id>')


if __name__ == '__main__':
    print('Running Flask app on port 5001')
    app.run(debug=True, host='0.0.0.0', port=5001)
