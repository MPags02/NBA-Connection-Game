from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_caching import Cache
import random
<<<<<<< Updated upstream
import requests
from nba_api.stats.endpoints import commonplayerinfo, playercareerstats, commonteamroster
from nba_api.stats.static import players
=======
import nfl_data_py as nfl
from nba_api.stats.endpoints import commonplayerinfo, playercareerstats, commonteamroster, teamdetails
from nba_api.stats.static import players as nba_players
import json
import logging
import os
>>>>>>> Stashed changes

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

<<<<<<< Updated upstream
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
=======
# Load cached team rosters from JSON file
with open('all_team_rosters.json', 'r') as f:
    all_team_rosters = json.load(f)


import os
from nba_api.stats.endpoints import commonteamroster
import json

def cache_all_team_rosters():
    start_year = 2000
    current_year = 2024
    all_rosters = {}

    for year in range(start_year, current_year + 1):
        season = f"{year}-{str(year + 1)[-2:]}"
        all_rosters[season] = {}
        for team_id in range(1610612737, 1610612766):  # Team IDs range from 1610612737 to 1610612766
            try:
                roster = commonteamroster.CommonTeamRoster(team_id=team_id, season=season).get_data_frames()[0]
                all_rosters[season][team_id] = roster.to_dict(orient='records')
            except Exception as e:
                print(f"Failed to get roster for team {team_id} in season {season}: {e}")
    
    # Save to a JSON file
    with open('all_team_rosters.json', 'w') as json_file:
        json.dump(all_rosters, json_file, indent=4)

    print("All team rosters have been cached.")


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

logging.basicConfig(level=logging.DEBUG)

def get_player_image(player_id, sport):
    if sport == 'nba':
        url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
    else:
        player_id_str = str(player_id)
        url = f"https://www.pro-football-reference.com/players/{player_id_str[0]}/{player_id_str}.jpg"
    
    logging.debug(f"Generated URL for {sport} player: {url}")
    return url


@cache.memoize(60*60)
def get_player_teammates(player_id, sport):
    teammates = set()
    if sport == 'nba':
        career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        team_data = career_stats.get_data_frames()[0]

        # Iterate over each row to collect teammates from all teams in all seasons
        for _, row in team_data.iterrows():
            team_id = row['TEAM_ID']
            season = row['SEASON_ID']
            roster = get_team_roster(team_id, season)
            teammates.update(roster)
    else:  # nfl
        rosters = nfl.import_seasonal_rosters([2023])
        player_team = rosters[rosters['player_id'] == player_id]['team'].values[0]
        teammates = set(rosters[rosters['team'] == player_team]['player_id'].tolist())
    
    return teammates



import random

def find_two_players_with_common_teammate(sport):
    active_player_ids = get_active_player_ids(sport)
    
    player1_id = random.choice(active_player_ids)
    player1_teammates = get_player_teammates(player1_id, sport)
    
    potential_player2_ids = active_player_ids[:]
    random.shuffle(potential_player2_ids)
    
    for player2_id in potential_player2_ids:
        if player2_id == player1_id:
            continue
        
        player2_teammates = get_player_teammates(player2_id, sport)
        common_teammates = player1_teammates.intersection(player2_teammates)

        if common_teammates:
            return player1_id, player2_id, common_teammates
    
    return find_two_players_with_common_teammate(sport)






@cache.memoize(60*60)
def get_team_roster(team_id, season):
    # Use cached rosters instead of calling the API
    season_str = str(season)  # Ensure the season is in string format like '2000-01'
    if season_str in all_team_rosters and str(team_id) in all_team_rosters[season_str]:
        roster = all_team_rosters[season_str][str(team_id)]
        return [player['PLAYER_ID'] for player in roster]
    else:
        return []

>>>>>>> Stashed changes

# Filter active players
@cache.memoize(60*60)  # Cache for 1 hour
def get_active_player_ids():
    player_dict = players.get_active_players()
    active_player_ids = [player['id'] for player in player_dict]
    return active_player_ids

<<<<<<< Updated upstream
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
=======
@app.route('/')
def menu():
    return render_template('menu.html')

@app.route('/cache_team_rosters', methods=['GET'])
def cache_team_rosters():
    cache_all_team_rosters()
    return redirect(url_for('menu'))


@app.route('/nba/')
def index():
    if 'rounds' not in session:
        session['rounds'] = 0
    if 'successes' not in session:
        session['successes'] = 0

    # Alternate between question types
    question_type = random.choice(['teammate', 'team_and_year'])
    
    if question_type == 'teammate':
        player1_id, player2_id, common_teammates = find_two_players_with_common_teammate('nba')
        session['question_type'] = 'teammate'
        session['common_teammates'] = list(common_teammates)
    else:
        player1_id, player2_id, common_team_years = find_two_players_with_common_team_and_year()
        session['question_type'] = 'team_and_year'
        session['common_team_years'] = common_team_years  # Store the list of common team years

    # Get player info for display
    player1_info = commonplayerinfo.CommonPlayerInfo(player_id=player1_id).common_player_info.get_dict()['data'][0]
    player2_info = commonplayerinfo.CommonPlayerInfo(player_id=player2_id).common_player_info.get_dict()['data'][0]

    player1_name = player1_info[3]
    player2_name = player2_info[3]

    player1_image = get_player_image(player1_id, 'nba')
    player2_image = get_player_image(player2_id, 'nba')

    return render_template('index.html', sport='nba', player1_name=player1_name, player2_name=player2_name, player1_image=player1_image, player2_image=player2_image, rounds=session['rounds'], successes=session['successes'], question_type=question_type)

@app.route('/nba/players')
@cache.memoize(60*60)
def get_players():
    
    with open('nba_players.json') as f:
        player_names = json.load(f)
    
    return jsonify(player_names)

@app.route('/refresh_players')
def refresh_players():
    nba_player_dict = nba_players.get_players()
    nba_player_names = [player['full_name'] for player in nba_player_dict]
    with open('nba_players.json', 'w') as f:
        json.dump(nba_player_names, f)

    nfl_rosters = nfl.import_seasonal_rosters([2023])
    nfl_player_names = nfl_rosters['player_name'].tolist()
    with open('nfl_players.json', 'w') as f:
        json.dump(nfl_player_names, f)

    return redirect(url_for('menu'))

@app.route('/nba/guess', methods=['POST'])
def guess():
    player1_name = request.form['player1_name']
    player2_name = request.form['player2_name']
    question_type = session.get('question_type')

    session['rounds'] += 1

    if question_type == 'teammate':
        guessed_teammate = request.form['guessed_teammate']
        guessed_teammate_id = get_player_id(guessed_teammate, 'nba')
        player1_id = get_player_id(player1_name, 'nba')
        player2_id = get_player_id(player2_name, 'nba')

        player1_teammates = get_player_teammates(player1_id, 'nba')
        player2_teammates = get_player_teammates(player2_id, 'nba')
        common_teammates = player1_teammates.intersection(player2_teammates)

        if guessed_teammate_id in common_teammates:
            session['successes'] += 1
            result = f"Correct! {guessed_teammate} has played with both {player1_name} and {player2_name}."
            guessed_teammate_image = get_player_image(guessed_teammate_id, 'nba')
            return render_template('result.html', sport='nba', result=result, rounds=session['rounds'], successes=session['successes'], win=True, guessed_teammate_image=guessed_teammate_image)
        else:
            correct_teammate_id = random.choice(list(common_teammates))
            correct_teammate_info = commonplayerinfo.CommonPlayerInfo(player_id=correct_teammate_id).common_player_info.get_dict()['data'][0]
            correct_teammate_name = correct_teammate_info[3]
            correct_teammate_image = get_player_image(correct_teammate_id, 'nba')
            result = f"{guessed_teammate} has not played with both {player1_name} and {player2_name}. One correct answer: {correct_teammate_name}. Try again."
            return render_template('result.html', sport='nba', result=result, rounds=session['rounds'], successes=session['successes'], win=False, correct_teammate_name=correct_teammate_name, correct_teammate_image=correct_teammate_image)

    elif question_type == 'team_and_year':
        guessed_team = request.form['guessed_team']
        guessed_year = request.form['guessed_year']

        correct_team_years = session.get('common_team_years', [])
        correct_guesses = [(team, year) for team, year in correct_team_years if team.lower() == guessed_team.lower() and guessed_year == year]

        if correct_guesses:
            session['successes'] += 1
            result = f"Correct! They played for {guessed_team} in {guessed_year}."
            return render_template('result.html', sport='nba', result=result, rounds=session['rounds'], successes=session['successes'], win=True)
        else:
            # Pick an example year to show the user
            example_team, example_year = correct_team_years[0]  # Pick the first correct answer as an example
            result = f"{player1_name} and {player2_name} did not both play for {guessed_team} in {guessed_year} year. Example: They played for {example_team} in {example_year}. Try again."
            return render_template('result.html', sport='nba', result=result, rounds=session['rounds'], successes=session['successes'], win=False)


@app.route('/reset')
def reset():
    session['rounds'] = 0
    session['successes'] = 0
    return redirect(url_for('menu'))

@app.route('/nba/teams-and-years')
@cache.memoize(60*60)
def get_teams_and_years():
    # List of all NBA teams (as of the latest season)
    teams = [
        "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets", 
        "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
        "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers", 
        "Los Angeles Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat", 
        "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks", 
        "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns", 
        "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", 
        "Utah Jazz", "Washington Wizards"
    ]

    # Generate list of years in the format 'YYYY-YY' from 2000-01 season to the current season
    current_year = 2024
    years = [f"{year}-{str(year + 1)[-2:]}" for year in range(2000, current_year)]

    return jsonify({'teams': teams, 'years': years})



def find_two_players_with_common_team_and_year():
    active_player_ids = get_active_player_ids('nba')
>>>>>>> Stashed changes

    while True:
        player1_id = random.choice(active_player_ids)
        player1_stats = playercareerstats.PlayerCareerStats(player_id=player1_id).get_data_frames()[0]
        
        while True:
            selected_row = player1_stats.sample(n=1).iloc[0]
            common_team_id = selected_row['TEAM_ID']
            common_year = selected_row['SEASON_ID']
            
            roster = get_team_roster(common_team_id, common_year)
            if roster:
                break
        
        player2_id = random.choice(roster)
        
        if player2_id == player1_id:
            continue
        
<<<<<<< Updated upstream
        player1_teammates = get_player_teammates(player1_id)
        player2_teammates = get_player_teammates(player2_id)
        common_teammates = player1_teammates.intersection(player2_teammates)
=======
        player2_stats = playercareerstats.PlayerCareerStats(player_id=player2_id).get_data_frames()[0]
        common_teams = player1_stats.merge(player2_stats, on=['TEAM_ID', 'SEASON_ID'], suffixes=('_player1', '_player2'))

        if not common_teams.empty:
            common_team_years = []
            for _, common_team in common_teams.iterrows():
                common_team_id = common_team['TEAM_ID']
                common_year = common_team['SEASON_ID']
                
                team_info = get_team_info(common_team_id)
                common_team_name = f"{team_info['CITY']} {team_info['NICKNAME']}"
                
                common_team_years.append((common_team_name, common_year))
            
            return player1_id, player2_id, common_team_years









def get_team_info(team_id):
    # Retrieve the team details from the TeamDetails endpoint
    team_details = teamdetails.TeamDetails(team_id=team_id).get_data_frames()
    
    # TeamBackground contains CITY and NICKNAME
    team_background = team_details[0]  # The first DataFrame usually contains the background details
    
    # Check if the DataFrame is empty before trying to access its content
    if team_background.empty:
        logging.error(f"No data found for team_id: {team_id}")
        return {'CITY': 'Unknown', 'NICKNAME': 'Unknown'}
    
    # Safely access the first row
    team_info = {
        'CITY': team_background.iloc[0]['CITY'],
        'NICKNAME': team_background.iloc[0]['NICKNAME'],
    }
    return team_info






>>>>>>> Stashed changes


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
