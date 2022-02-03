from flask import Flask
import sharks_ice_lib as sil

app = Flask(__name__)


@app.route('/game/<game_id>')
def game(game_id):
    return sil.load_game_json(game_id)

@app.route('/team/<team_id>')
def team(team_id):
    return sil.load_team_json(team_id)

@app.route('/')
def api():
    return sil.load_divisions_json()

if __name__ == '__main__':
    print('Running Flask app on port 5001')
    app.run(debug=True, host='0.0.0.0', port=5001)
