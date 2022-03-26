import pandas as pd
import util
import datetime

TIMETOSCORE_URL = 'https://stats.sharksice.timetoscore.com/'
TEAM_URL = TIMETOSCORE_URL + 'display-schedule'
GAME_URL = TIMETOSCORE_URL + 'oss-scoresheet'
DIVISION_URL = TIMETOSCORE_URL + 'display-league-stats'
MAIN_STATS_URL = TIMETOSCORE_URL + 'display-stats.php'


td_selectors = dict(
    # Game stats
    date="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(1)",
    time="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(2)",
    league="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(1)",
    level="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(3) > td:nth-child(1)",
    location="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(4) > td:nth-child(1)",
    scorekeeper="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(2) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(2)",
    periodLength="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(4) > td:nth-child(2)",
    referee1="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(2) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(2)",
    referee2="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(2) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(3) > td:nth-child(2)",
    visitor="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(2)",
    home="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(3) > td:nth-child(2)",
    # Selectors we'll use to verify that parsing other parts were correct.
    visitorGoals="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(7)",
    homeGoals="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(3) > td:nth-child(7)",
)

tr_selectors = dict(    
    visitorPlayers="body > table:nth-child(3) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(1) > table:nth-child(2) > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(n+2)",
    homePlayers="body > table:nth-child(3) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(2) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(n+2)",
    visitorScoring="body > div > div.d50l > div.d25l > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(n+4)",
    homeScoring="body > div > div.d50r > div.d25l > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(n+4)",
    visitorPenalties="body > div > div.d50l > div.d25r > table:nth-child(1) > tbody:nth-child(1) > tr",
    homePenalties="body > div > div.d50r > div.d25r > table:nth-child(1) > tbody:nth-child(1) > tr",
    visitorShootout="body > div > div.d50l > div.d25l > table:nth-child(2) > tbody:nth-child(1) > tr:nth-child(n+4)",
    homeShootout="body > div > div.d50r > div.d25l > table:nth-child(2) > tbody:nth-child(1) > tr:nth-child(n+4)",
    
)

columns = dict(
    players=['number', 'position', 'name'],
    penalties=['period', 'number', 'infraction',
               'minutes', 'offIce', 'start', 'end', 'onIce'],
    scoring=['period', 'time', 'extra', 'goal', 'assist1', 'assist2'],
    shootout=['number', 'player', 'result'],
)

team_columns_rename = {
    'GP': 'gamesPlayed',
    'W': 'wins',
    'T': 'ties',
    'L': 'losses',
    'OTL': 'overtimeLosses',
    'PTS': 'points',
    'Streak': 'streak',
    'Tie Breaker': 'tieBreaker',
}

player_columns_rename = {
    'Team': 'team',
    'Name': 'name',
    '#': 'number',
    'GP': 'gamesPlayed',
    'Ass.': 'assists',
    'Goals': 'goals',
    'Pts': 'points',
    'Pts/Game': 'pointsPerGame',
    'Hat': 'hatTricks',
    'Min': 'penaltyMinutes',
}

goalie_columns_rename = {
    'Team': 'team',
    'Name': 'name',
    'GP': 'gamesPlayed',
    'Shots': 'shots',
    'GA': 'goalsAgainst',
    'GAA': 'goalsAgainstAverage',
    'Save %': 'savePercentage',
    'SO': 'shutouts',
}

game_columns_rename = {
    'Game': ('id', lambda g: g.replace('*', '').replace('^', '')),
    'Date': 'date',
    'Time': 'time',
    'Rink': 'rink',
    'League': 'league',
    'Level': 'level',
    'Away': 'away',
    'Home': 'home',
    'Type': 'type',
    'Goals.1': 'homeGoals',
    'Goals': 'visitorGoals',
    'Scoresheet': None,
    'Box Score': None,
}


class Error(Exception):
    pass


class MissingStatsError(Error):
    pass


def rename(initial: dict, mapping: dict):
    new_map = {}
    for key, val in initial.items():
        mapped_key = mapping.get(key, key)
        if mapped_key is None:
            continue
        if isinstance(mapped_key, tuple):
            mapped_key, func = mapped_key
            val = func(val)
        new_map[mapped_key] = val
    return new_map


def dedupe(headers):
    counts = {}
    cols = []
    for i, col in enumerate(headers):
        counts[col] = counts.get(col, 0) + 1
        if counts[col] > 1:
            col += str(counts[col])
        cols.append(col)
    return cols


def parse_td_row(row):
    val = []
    for td in row('td'):
        if td('a'):
            val.append({'text': td.a.text.strip(), 'link': td.a['href']})
        else:
            val.append(td.text.strip())
    return val


def load_table(header_row):
    table = []
    if not header_row:
        return table
    columns = [t.text.strip() for t in header_row.find_all('th')]
    columns = dedupe(columns)
    row = header_row.next_sibling
    while row:
        tds = parse_td_row(row)
        if len(tds) <= 1:
            break
        table.append(dict(zip(columns, tds)))
        row = row.next_sibling
    return table


def fix_players_rows(rows):
    val = []
    for row in rows:
        val.append(row[:3])
        if len(row) == 6:
            val.append(row[3:])
    return val


@util.cache_json('seasons')
def get_seasons():
    soup = util.get_html(MAIN_STATS_URL, params={'league': '1'})
    season_ids = {o.text.strip(): int(o['value'])
                  for o in soup.find('select')('option')}
    # Hack to use real season ID instead of "0" for current season.
    season_ids['Current'] = max(season_ids.values()) + 1
    return season_ids


def get_current_season():
    return get_seasons()['Current']

def get_team_id(name):
    for div in get_divisions():
        if div['name'] == name:
            return div['id']
    raise Exception('Could not find team: %s' % name)


def _load_division(row):
    div_name = row.th.text.strip()[15:]
    # Get Div ID from next row.
    href = row.next_sibling.a['href'].strip()
    level_id = util.get_value_from_link(href, 'level')
    conference_id = util.get_value_from_link(href, 'conf')
    season_id = util.get_value_from_link(href, 'season')
    # Jump down to teams subtable header row.
    while len(row('th')) == 1:
        row = row.next_sibling
    teams = []
    for team_row in load_table(row):
        team_a = team_row.pop('Team')
        team_row['name'] = team_a['text']
        team_row['id'] = util.get_value_from_link(team_a['link'], 'team')
        team_row = rename(team_row, team_columns_rename)
        teams.append(team_row)
    return {
        'name': div_name,
        'id': level_id,
        'conferenceId': conference_id,
        'seasonId': season_id,
        'teams': teams,
    }


# JSON helpers for REST API
@util.cache_json('seasons/{season_id}/divisions', max_age=datetime.timedelta(hours=1))
def get_divisions(season_id: int, reload=False) -> list:
    soup = util.get_html(MAIN_STATS_URL, params=dict(
        league=1, season=season_id))
    divisions = []
    for row in soup.table.find_all('tr'):
        if not row.th:
            continue
        if row.th.text.startswith('Adult Division'):
            divisions.append(_load_division(row))
    return divisions


@util.cache_json('seasons/{season_id}/division/{div_id}#{conference_id}_players', max_age=datetime.timedelta(minutes=10))
def get_division_players(div_id: str, conference_id: str, season_id: str, reload=False):
    if season_id.lower() == 'current':
        season_id = get_current_season()
    html = util.get_html(DIVISION_URL, params=dict(
        level=div_id, conf=conference_id, season=season_id, league=1))
    if not html.find('table'):
        raise Exception('Error loading division stats for division ID %s (conference %s)' % (
            div_id, conference_id))
    player_table, goalie_table = pd.read_html(str(html), header=1)
    player_table.fillna('', inplace=True)
    goalie_table.fillna('', inplace=True)
    players, goalies = [], []
    for _, row in player_table.iterrows():
        row = rename(row.to_dict(), player_columns_rename)
        players.append(row)
    for _, row in goalie_table.iterrows():
        row = rename(row.to_dict(), goalie_columns_rename)
        goalies.append(row)
    return players, goalies


@util.cache_json('seasons/{season_id}/teams/{team_id}')
def get_team(season_id: int, team_id: int, reload=False):
    info = {}
    soup = util.get_html(TEAM_URL, params=dict(season=season_id, team=team_id))
    if not soup.table:
        return {}
    webcal = [a['href']
              for a in soup.find_all('a') if 'WebCal' in a.text.strip()]
    if webcal:
        info['calendar'] = webcal[0]

    games = []
    results = pd.read_html(str(soup.table), header=1)[0]
    results.fillna('', inplace=True)
    for _, row in results.iterrows():
        row = rename(row.to_dict(), game_columns_rename)
        games.append(row)
    info['games'] = games
    return info


@util.cache_json('games/{game_id}', max_age=None)
def get_game_stats(game_id: int, reload=False):
    soup = util.get_html(
        GAME_URL, params=dict(game_id=game_id))
    if not soup.select_one(td_selectors['periodLength']):
        raise MissingStatsError("No game stats for %s" % game_id)
    data = {}
    for name, selector in td_selectors.items():
        ele = soup.select_one(selector)
        val = ele.text.strip()
        if ':' in val:
            val = val.split(':', 1)[1]
        data[name] = val

    for name, selector in tr_selectors.items():
        prefix = 'home' if name.startswith('home') else 'visitor'
        suffix = name[len(prefix):].lower()
        eles = soup.select(selector)
        rows = [parse_td_row(row) for row in eles if row('td')]
        # Hack for players tables.
        if name.endswith('Players'):
            rows = fix_players_rows(rows)
        val = [dict(zip(columns[suffix], row)) for row in rows]
        data[name] = val
    return data


def test():
    divs = get_divisions(season_id='current')
    div_players = {}
    for div in divs:
        print('Loading players for %s#%s' % (div['id'], div['conferenceId']))
        div_players[div['id']] = get_division_players(
            div_id=div['id'], conference_id=div['conferenceId'], season_id=div['seasonId'])
        
    teams = []
    for div in divs:
        for team in div['teams']:
            print('Loading games for %s' % team['id'])
            teams.append(get_team(season_id='current', team_id=team['id']))
    for team in teams:
        for game in team['games']:
            game_time = util.parse_game_time(game['Date'], game['Time'])
            if game_time >= datetime.datetime.now():
                print('Skipping game in the future')
                continue
            print('Loading stats for %s' % game['id'])
            try:
                stats = get_game_stats(game_id=game['id'])
            except MissingStatsError:
                pass


if __name__ == '__main__':
    if input('test all?') == 'y':
        test()
    pass
