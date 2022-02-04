from flask import Flask, jsonify
import sharks_ice_lib as sil
from flask_restful import Resource, Api


app = Flask(__name__)
api = Api(app)


class Division(Resource):
  def get(self):
    return jsonify(sil.load_divisions())

class Team(Resource):
  def get(self, team_id):
    return jsonify(sil.load_team(team_id))

class Game(Resource):
  def get(self, game_id):
    return jsonify(sil.load_game(game_id))

api.add_resource(Team, '/team/<string:team_id>')
api.add_resource(Game, '/game/<string:game_id>')
api.add_resource(Division, '/')


if __name__ == '__main__':
    print('Running Flask app on port 5001')
    app.run(debug=True, host='0.0.0.0', port=5001)
