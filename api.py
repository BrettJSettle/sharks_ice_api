from flask import Flask, jsonify, request
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
                '/seasons',
                '/seasons/<seasonId>/divisions',
                '/seasons/<seasonId>/divisions/<divisionId>/conference/<conferenceId>',
                '/seasons/<seasonId>/teams/<teamId>',
                '/games/<gameId>',
            ]
        })


class Seasons(Resource):
    def get(self):
        try:
            return jsonify({'seasons': sil.get_seasons()})
        except sil.Error as e:
            return jsonify({'error': str(e)}), 500


class Divisions(Resource):
    def get(self, season_id: str):
        try:
            return jsonify({'divisions': sil.get_divisions(season_id=season_id)})
        except sil.Error as e:
            return jsonify({'error': str(e)})


class DivisionPlayers(Resource):
    def get(self, season_id: str, division_id: int, conference_id: str = '0'):
        try:
            players, goalies = sil.get_division_players(
                div_id=division_id, season_id=season_id, conference_id=conference_id, reload=get_reload())
            return jsonify({
                'players': players,
                'goalies': goalies
            })
        except sil.Error as e:
            return jsonify({'error': str(e)})


class Team(Resource):
    def get(self, season_id: str, team_id: str):
        try:
            return jsonify(sil.get_team(season_id=season_id, team_id=team_id, reload=get_reload()))
        except sil.Error as e:
            return jsonify({'error': str(e)})


class TeamName(Resource):
    def get(self, season_id: str):
        try:
            team_id = sil.get_team_id(season_id=season_id, team_name=request.args.get('team'))
            return jsonify(sil.get_team(season_id=season_id, team_id=team_id, reload=get_reload()))
        except sil.Error as e:
            return jsonify({'error': str(e)})


class Game(Resource):
    def get(self, game_id: str):
        try:
            return jsonify(sil.get_game_stats(game_id=game_id, reload=get_reload()))
        except sil.Error as e:
            return jsonify({'error': str(e)})


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return '404 Page Not Found', 404


api.add_resource(Main, '/')
api.add_resource(Seasons, '/seasons')
api.add_resource(Divisions, '/seasons/<string:season_id>/divisions')
api.add_resource(DivisionPlayers,
                 '/seasons/<string:season_id>/divisions/<int:division_id>/conference/<string:conference_id>',
                 '/seasons/<string:season_id>/divisions/<int:division_id>')
api.add_resource(Team, '/seasons/<string:season_id>/teams/<int:team_id>')
api.add_resource(TeamName, '/seasons/<string:season_id>/teams')
api.add_resource(Game, '/games/<int:game_id>')


if __name__ == '__main__':
    print('Running Flask app on port 5001')
    app.run(debug=True, host='0.0.0.0', port=5001)
