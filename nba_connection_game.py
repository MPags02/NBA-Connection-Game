from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_caching import Cache
import random
import nfl_data_py as nfl
from nba_api.stats.endpoints import commonplayerinfo, playercareerstats, commonteamroster
from nba_api.stats.static import players as nba_players

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@cache.memoize(60*60)  # Cache for 1 hour
def get_player_id(player_name, sport):
    if sport == 'nba':
        player_dict = nba_players.get_players()
        player = next((player for player in player_dict if player['full_name'].lower() == player_name.lower()), None)
        return player['id'] if player else None
    else:  # nfl
        players_df = nfl.import_seasonal_rosters([2023])
        player = players_df[players_df['player_name'].str.lower() == player_name.lower()]
        return player['player_id'].values[0] if not player.empty else None

def get_player_image(player_id, sport):
    if sport == 'nba':
        return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
    else:
        players_df = nfl.import_seasonal_rosters([2023])
        player = players_df[players_df['player_id'] == player_id]
        return player['headshot_url'].values[0] if not player.empty else ""

@cache.memoize(60*60)  # Cache for 1 hour
def get_player_teammates(player_id, sport, season=None):
    teammates = set()
    if sport == 'nba':
        career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        team_data = career_stats.get_data_frames()[0]
        teams = team_data['TEAM_ID'].unique()
        for team in teams:
            roster = get_team_roster(team, sport)
            teammates.update(roster)
    else:  # nfl
        players_df = nfl.import_seasonal_rosters([season or 2023])
        team_id = players_df[players_df['player_id'] == player_id]['team'].values[0]
        team_roster = players_df[players_df['team'] == team_id]
        teammates = set(team_roster['player_id'].values)
        teammates.discard(player_id)
    return teammates

@cache.memoize(60*60)  # Cache for 1 hour
def get_team_roster(team_id, sport, season=None):
    player_ids = []
    if sport == 'nba':
        roster = commonteamroster.CommonTeamRoster(team_id=team_id).get_data_frames()[0]
        player_ids = roster['PLAYER_ID'].tolist()
    else:  # nfl
        players_df = nfl.import_seasonal_rosters([season or 2023])
        team_roster = players_df[players_df['team'] == team_id]
        player_ids = team_roster['player_id'].tolist()
    return player_ids

@cache.memoize(60*60)  # Cache for 1 hour
def get_active_player_ids(sport, season=None):
    if sport == 'nba':
        player_dict = nba_players.get_active_players()
        return [player['id'] for player in player_dict]
    else:  # nfl
        players_df = nfl.import_seasonal_rosters([season or 2023])
        return players_df['player_id'].tolist()

@app.route('/')
def menu():
    return render_template('menu.html')

@app.route('/<sport>/')
def index(sport):
    if 'rounds' not in session:
        session['rounds'] = 0
    if 'successes' not in session:
        session['successes'] = 0

    player1_id, player2_id, common_teammates = find_two_players_with_common_teammate(sport)
    player1_info = commonplayerinfo.CommonPlayerInfo(player_id=player1_id).common_player_info.get_dict()['data'][0] if sport == 'nba' else nfl.import_seasonal_rosters([2023])[nfl.import_seasonal_rosters([2023])['player_id'] == player1_id]
    player2_info = commonplayerinfo.CommonPlayerInfo(player_id=player2_id).common_player_info.get_dict()['data'][0] if sport == 'nba' else nfl.import_seasonal_rosters([2023])[nfl.import_seasonal_rosters([2023])['player_id'] == player2_id]

    player1_name = player1_info[3] if sport == 'nba' else player1_info['player_name'].values[0]
    player2_name = player2_info[3] if sport == 'nba' else player2_info['player_name'].values[0]

    player1_image = get_player_image(player1_id, sport)
    player2_image = get_player_image(player2_id, sport)

    session['common_teammates'] = list(common_teammates)
    session['sport'] = sport

    return render_template('index.html', sport=sport, player1_name=player1_name, player2_name=player2_name, player1_image=player1_image, player2_image=player2_image, common_teammates=common_teammates, rounds=session['rounds'], successes=session['successes'])

@app.route('/<sport>/players')
@cache.memoize(60*60)
def get_players(sport):
    if sport == 'nba':
        player_dict = nba_players.get_players()
        player_names = [player['full_name'] for player in player_dict]
    else:
        players_df = nfl.import_seasonal_rosters([2023])
        player_names = players_df['player_name'].tolist()
    return jsonify(player_names)

@app.route('/<sport>/guess', methods=['POST'])
def guess(sport):
    player1_name = request.form['player1_name']
    player2_name = request.form['player2_name']
    guessed_teammate = request.form['guessed_teammate']

    guessed_teammate_id = get_player_id(guessed_teammate, sport)
    player1_id = get_player_id(player1_name, sport)
    player2_id = get_player_id(player2_name, sport)

    player1_teammates = get_player_teammates(player1_id, sport)
    player2_teammates = get_player_teammates(player2_id, sport)
    common_teammates = player1_teammates.intersection(player2_teammates)

    session['rounds'] += 1

    if guessed_teammate_id in common_teammates:
        session['successes'] += 1
        result = f"Correct! {guessed_teammate} has played with both {player1_name} and {player2_name}."
        guessed_teammate_image = get_player_image(guessed_teammate_id, sport)
        return render_template('result.html', sport=sport, result=result, rounds=session['rounds'], successes=session['successes'], win=True, guessed_teammate_image=guessed_teammate_image)
    else:
        correct_teammate_id = random.choice(list(common_teammates))
        correct_teammate_info = commonplayerinfo.CommonPlayerInfo(player_id=correct_teammate_id).common_player_info.get_dict()['data'][0] if sport == 'nba' else nfl.import_seasonal_rosters([2023])[nfl.import_seasonal_rosters([2023])['player_id'] == correct_teammate_id]
        correct_teammate_name = correct_teammate_info[3] if sport == 'nba' else correct_teammate_info['player_name'].values[0]
        correct_teammate_image = get_player_image(correct_teammate_id, sport)
        result = f"{guessed_teammate} has not played with both {player1_name} and {player2_name}. Try again."
        return render_template('result.html', sport=sport, result=result, rounds=session['rounds'], successes=session['successes'], win=False, correct_teammate_name=correct_teammate_name, correct_teammate_image=correct_teammate_image)

@app.route('/reset')
def reset():
    session['rounds'] = 0
    session['successes'] = 0
    return redirect(url_for('menu'))

def find_two_players_with_common_teammate(sport):
    active_player_ids = get_active_player_ids(sport)

    while True:
        player1_id = random.choice(active_player_ids)
        player2_id = random.choice(active_player_ids)
        
        if player1_id == player2_id:
            continue
        
        player1_teammates = get_player_teammates(player1_id, sport)
        player2_teammates = get_player_teammates(player2_id, sport)
        common_teammates = player1_teammates.intersection(player2_teammates)

        if common_teammates:
            return player1_id, player2_id, common_teammates

if __name__ == '__main__':
    app.run(debug=True)
