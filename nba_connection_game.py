from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_caching import Cache
import random
from nba_api.stats.endpoints import commonplayerinfo, playercareerstats, commonteamroster, teamdetails
from nba_api.stats.static import players as nba_players
import json
import logging
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
cache = Cache(app, config={'CACHE_TYPE': 'simple'})


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
    sport == 'nba'
    player_dict = nba_players.get_players()
    player = next((player for player in player_dict if player['full_name'].lower() == player_name.lower()), None)
    return player['id'] if player else None


logging.basicConfig(level=logging.DEBUG)

def get_player_image(player_id, sport):
    if sport == 'nba':
        url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
    else:
        player_id_str = str(player_id)
        url = f"https://www.pro-football-reference.com/players/{player_id_str[0]}/{player_id_str}.jpg"
    
    logging.debug(f"Generated URL for {sport} player: {url}")
    return url


@cache.memoize(60*60)  # Cache for 1 hour
def get_team_roster(team_id, season, sport):
    player_ids = []
    if sport == 'nba':
        roster = commonteamroster.CommonTeamRoster(team_id=team_id, season=season).get_data_frames()[0]
        player_ids = roster['PLAYER_ID'].tolist()
  
        
    return player_ids

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
            roster = get_team_roster(team_id, season, sport)
            teammates.update(roster)
  
    
    return teammates


import random

def find_two_players_with_common_teammate(sport):
    active_player_ids = get_active_player_ids(sport)
    
    # Step 1: Select the first player and retrieve their teammates
    player1_id = random.choice(active_player_ids)
    player1_teammates = get_player_teammates(player1_id, sport)
    
    # Step 2: Shuffle the list of active players to randomize the order for Player 2 selection
    potential_player2_ids = active_player_ids[:]
    random.shuffle(potential_player2_ids)
    
    # Step 3: Iterate through shuffled players to find one with a common teammate
    for player2_id in potential_player2_ids:
        if player2_id == player1_id:
            continue
        
        player2_teammates = get_player_teammates(player2_id, sport)
        common_teammates = player1_teammates.intersection(player2_teammates)

        if common_teammates:
            return player1_id, player2_id, common_teammates
    
    # If no common teammate is found, try again (this should be rare)
    return find_two_players_with_common_teammate(sport)






@cache.memoize(60*60)  # Cache for 1 hour
def get_active_player_ids(sport):
    if sport == 'nba':
        player_dict = nba_players.get_active_players()
        return [player['id'] for player in player_dict]


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
    question_type = random.choice(['teammate', 'team_and_year', 'headshot']) #add question guess player from image
    #question_type = 'headshot' #testing
    
    if question_type == 'teammate':
        player1_id, player2_id, common_teammates = find_two_players_with_common_teammate('nba')
        session['question_type'] = 'teammate'
        session['common_teammates'] = list(common_teammates)
    elif question_type == 'team_and_year':
        player1_id, player2_id, common_team_years = find_two_players_with_common_team_and_year()
        session['question_type'] = 'team_and_year'
        session['common_team_years'] = common_team_years  # Store the list of common team years
    elif question_type == 'headshot':
            # Step 1: Get a list of active NBA players
        active_player_ids = get_active_player_ids('nba')

        # Step 2: Randomly select one player's ID
        player_id = random.choice(active_player_ids)

        # Step 3: Set the question type in session and store the player ID
        session['question_type'] = 'headshot'
        session['player_id'] = player_id

        # Step 4: Retrieve player information
        player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id).common_player_info.get_dict()['data'][0]
        player_name = player_info[3]

        # Step 5: Get player image URL
        player_image = get_player_image(player_id, 'nba')

        # Step 6: Render the page with player image and question details
        return render_template('index.html', sport='nba', player_name=player_name, player_image=player_image, rounds=session['rounds'], successes=session['successes'], question_type=question_type)

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
            display_image = get_player_image(guessed_teammate_id, 'nba')
            print(f"Guessed Teammate Image URL: {display_image}")  # For debugging
            
            return render_template('result.html', sport='nba', result=result, rounds=session['rounds'], successes=session['successes'], win=True, display_image=display_image)
        else:
            correct_teammate_id = random.choice(list(common_teammates))
            correct_teammate_info = commonplayerinfo.CommonPlayerInfo(player_id=correct_teammate_id).common_player_info.get_dict()['data'][0]
            correct_teammate_name = correct_teammate_info[3]
            display_image = get_player_image(correct_teammate_id, 'nba')
            print(f"Correct Teammate Image URL: {display_image}")  # For debugging
            result = f"{guessed_teammate} has not played with both {player1_name} and {player2_name}. One correct answer: {correct_teammate_name}. Try again."
            return render_template('result.html', sport='nba', result=result, rounds=session['rounds'], successes=session['successes'], win=False, correct_teammate_name=correct_teammate_name, display_image=display_image)

    elif question_type == 'team_and_year':
        guessed_team = request.form['guessed_team']
        guessed_year = request.form['guessed_year']

        correct_team_years = session.get('common_team_years', [])
        correct_guesses = [(team, year) for team, year in correct_team_years if team.lower() == guessed_team.lower() and guessed_year == year]

        if correct_guesses:
            session['successes'] += 1
            result = f"Correct! They played for {guessed_team} in {guessed_year}."
            team_id = correct_guesses[0][0]  # Get the team ID from the first correct guess
            display_image = get_team_logo_url(team_id)
            print(f"Correct Teammate Image URL: {display_image}")  # For debugging
            return render_template('result.html', sport='nba', result=result, rounds=session['rounds'], successes=session['successes'], win=True, display_image=display_image)
        else:
            # Pick an example year to show the user
            example_team, example_year = correct_team_years[0]  # Pick the first correct answer as an example
            team_id = example_team  # Assume that the team ID is stored in the variable
            display_image = get_team_logo_url(team_id)
            print(f"Correct Teammate Image URL: {display_image}")  # For debugging
            result = f"{player1_name} and {player2_name} did not both play for {guessed_team} in {guessed_year}. Example: They played for {example_team} in {example_year}. Try again."
            return render_template('result.html', sport='nba', result=result, rounds=session['rounds'], successes=session['successes'], win=False, display_image=display_image)
        
    elif question_type == 'headshot':
        guessed_player = request.form['guessed_player']
        guessed_player_id = get_player_id(guessed_player, 'nba')
        correct_player_id = session.get('player_id')

        if guessed_player_id == correct_player_id:
            session['successes'] += 1
            result = f"Correct! The player is {guessed_player}."
            display_image = get_player_image(correct_player_id, 'nba')
            return render_template('result.html', sport='nba', result=result, rounds=session['rounds'], successes=session['successes'], win=True, display_image=display_image)
        else:
            player_info = commonplayerinfo.CommonPlayerInfo(player_id=correct_player_id).common_player_info.get_dict()['data'][0]
            correct_player_name = player_info[3]
            result = f"Incorrect. The correct player was {correct_player_name}."
            display_image = get_player_image(correct_player_id, 'nba')
            return render_template('result.html', sport='nba', result=result, rounds=session['rounds'], successes=session['successes'], win=False, display_image=display_image)


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

    while True:
        # Step 1: Select the first player randomly
        player1_id = random.choice(active_player_ids)
        
        # Step 2: Retrieve the player's career stats
        player1_stats = playercareerstats.PlayerCareerStats(player_id=player1_id).get_data_frames()[0]
        
        # Step 3: Loop to find a valid team/season with a non-empty roster
        while True:
            # Randomly select a row (season/team) from player1's stats
            selected_row = player1_stats.sample(n=1).iloc[0]
            common_team_id = selected_row['TEAM_ID']
            common_year = selected_row['SEASON_ID']
            
            # Retrieve the team roster for that season
            roster = get_team_roster(common_team_id, common_year, 'nba')
            
            # Check if the roster is not empty
            if roster:
                break  # Exit loop if a valid roster is found
        
        # Step 4: Randomly select a teammate from the roster
        player2_id = random.choice(roster)
        
        # Ensure Player 2 is not the same as Player 1
        if player2_id == player1_id:
            continue  # Retry if the same player is selected
        
        # Step 5: Retrieve Player 2's career stats
        player2_stats = playercareerstats.PlayerCareerStats(player_id=player2_id).get_data_frames()[0]
        
        # Step 6: Ensure they played on the same team in the same season(s)
        common_teams = player1_stats.merge(player2_stats, on=['TEAM_ID', 'SEASON_ID'], suffixes=('_player1', '_player2'))

        if not common_teams.empty:
            common_team_years = []
            for _, common_team in common_teams.iterrows():
                common_team_id = common_team['TEAM_ID']
                common_year = common_team['SEASON_ID']
                
                # Get team info (e.g., city and nickname)
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

def get_team_logo_url(team_name):
    team_id = get_team_id(team_name)
    if team_id:
        return f"https://cdn.nba.com/logos/nba/{team_id}/primary/L/logo.svg"
    return None




def get_team_id(team_name):
    team_id_mapping = {
        "Atlanta Hawks": 1610612737,
        "Boston Celtics": 1610612738,
        "Brooklyn Nets": 1610612751,
        "Charlotte Hornets": 1610612766,
        "Chicago Bulls": 1610612741,
        "Cleveland Cavaliers": 1610612739,
        "Dallas Mavericks": 1610612742,
        "Denver Nuggets": 1610612743,
        "Detroit Pistons": 1610612765,
        "Golden State Warriors": 1610612744,
        "Houston Rockets": 1610612745,
        "Indiana Pacers": 1610612754,
        "Los Angeles Clippers": 1610612746,
        "Los Angeles Lakers": 1610612747,
        "Memphis Grizzlies": 1610612763,
        "Miami Heat": 1610612748,
        "Milwaukee Bucks": 1610612749,
        "Minnesota Timberwolves": 1610612750,
        "New Orleans Pelicans": 1610612740,
        "New York Knicks": 1610612752,
        "Oklahoma City Thunder": 1610612760,
        "Orlando Magic": 1610612753,
        "Philadelphia 76ers": 1610612755,
        "Phoenix Suns": 1610612756,
        "Portland Trail Blazers": 1610612757,
        "Sacramento Kings": 1610612758,
        "San Antonio Spurs": 1610612759,
        "Toronto Raptors": 1610612761,
        "Utah Jazz": 1610612762,
        "Washington Wizards": 1610612764
    }
    return team_id_mapping.get(team_name)









if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
else:
    application = app
