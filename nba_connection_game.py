from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_caching import Cache
import random
import requests
from nba_api.stats.endpoints import commonplayerinfo, playercareerstats, commonteamroster
from nba_api.stats.static import players

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Get player ID by name (note for commit)
@cache.memoize(60*60)  # Cache for 1 hour
def get_player_id(player_name):
    player_dict = players.get_players()
    player = next((player for player in player_dict if player['full_name'].lower() == player_name.lower()), None)
    if player:
        return player['id']
    else:
        return None

# Get player image URL
def get_player_image(player_id):
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"

# Get teammates of a player
@cache.memoize(60*60)  # Cache for 1 hour
def get_player_teammates(player_id):
    career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
    team_data = career_stats.get_data_frames()[0]  # Regular season stats
    teams = team_data['TEAM_ID'].unique()
    teammates = set()
    for team in teams:
        roster = get_team_roster(team)
        teammates.update(roster)
    return teammates

# Get roster of a team by team ID
@cache.memoize(60*60)  # Cache for 1 hour
def get_team_roster(team_id):
    roster = commonteamroster.CommonTeamRoster(team_id=team_id).get_data_frames()[0]
    player_ids = roster['PLAYER_ID'].tolist()
    return player_ids

# Filter active players
@cache.memoize(60*60)  # Cache for 1 hour
def get_active_player_ids():
    player_dict = players.get_active_players()
    active_player_ids = [player['id'] for player in player_dict]
    return active_player_ids

# New route to get player names
@app.route('/players')
@cache.memoize(60*60)  # Cache for 1 hour
def get_players():
    player_dict = players.get_players()
    player_names = [player['full_name'] for player in player_dict]
    return jsonify(player_names)

# Find two players with common teammates
def find_two_players_with_common_teammate():
    active_player_ids = get_active_player_ids()

    while True:
        player1_id = random.choice(active_player_ids)
        player2_id = random.choice(active_player_ids)
        
        if player1_id == player2_id:
            continue
        
        player1_teammates = get_player_teammates(player1_id)
        player2_teammates = get_player_teammates(player2_id)
        common_teammates = player1_teammates.intersection(player2_teammates)

        if common_teammates:
            return player1_id, player2_id, common_teammates

@app.route('/')
def index():
    if 'rounds' not in session:
        session['rounds'] = 0
    if 'successes' not in session:
        session['successes'] = 0

    player1_id, player2_id, common_teammates = find_two_players_with_common_teammate()
    player1_info = commonplayerinfo.CommonPlayerInfo(player_id=player1_id).common_player_info.get_dict()['data'][0]
    player2_info = commonplayerinfo.CommonPlayerInfo(player_id=player2_id).common_player_info.get_dict()['data'][0]

    player1_name = player1_info[3]
    player2_name = player2_info[3]

    player1_image = get_player_image(player1_id)
    player2_image = get_player_image(player2_id)

    session['common_teammates'] = list(common_teammates)

    return render_template('index.html', player1_name=player1_name, player2_name=player2_name, player1_image=player1_image, player2_image=player2_image, common_teammates=common_teammates, rounds=session['rounds'], successes=session['successes'])

@app.route('/guess', methods=['POST'])
def guess():
    player1_name = request.form['player1_name']
    player2_name = request.form['player2_name']
    guessed_teammate = request.form['guessed_teammate']

    guessed_teammate_id = get_player_id(guessed_teammate)
    player1_id = get_player_id(player1_name)
    player2_id = get_player_id(player2_name)

    player1_teammates = get_player_teammates(player1_id)
    player2_teammates = get_player_teammates(player2_id)
    common_teammates = player1_teammates.intersection(player2_teammates)

    session['rounds'] += 1

    if guessed_teammate_id in common_teammates:
        session['successes'] += 1
        result = f"Correct! {guessed_teammate} has played with both {player1_name} and {player2_name}."
        guessed_teammate_image = get_player_image(guessed_teammate_id)
        return render_template('result.html', result=result, rounds=session['rounds'], successes=session['successes'], win=True, guessed_teammate_image=guessed_teammate_image)
    else:
        correct_teammate_id = random.choice(list(common_teammates))
        correct_teammate_info = commonplayerinfo.CommonPlayerInfo(player_id=correct_teammate_id).common_player_info.get_dict()['data'][0]
        correct_teammate_name = correct_teammate_info[3]
        correct_teammate_image = get_player_image(correct_teammate_id)
        result = f"{guessed_teammate} has not played with both {player1_name} and {player2_name}. Try again."
        return render_template('result.html', result=result, rounds=session['rounds'], successes=session['successes'], win=False, correct_teammate_name=correct_teammate_name, correct_teammate_image=correct_teammate_image)

@app.route('/reset')
def reset():
    session['rounds'] = 0
    session['successes'] = 0
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
