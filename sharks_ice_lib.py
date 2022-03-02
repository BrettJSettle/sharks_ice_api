import pandas as pd
import util
import datetime

TIMETOSCORE_URL = 'https://stats.sharksice.timetoscore.com/'
TEAM_URL = TIMETOSCORE_URL + 'display-schedule?team={team_id}'
GAME_URL = TIMETOSCORE_URL + 'oss-scoresheet?game_id={game_id}'
DIVISION_URL = TIMETOSCORE_URL + \
    'display-league-stats?league=1&level={division_id}&conf={conference_id}&season={season_id}'
MAIN_STATS_URL = TIMETOSCORE_URL + 'display-stats.php'


selectors = dict(
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
    # Team stats
    visitor="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(2)",
    home="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(3) > td:nth-child(2)",
    visitorPlayers="body > table:nth-child(3) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(1) > table:nth-child(2) > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(n+2)",
    homePlayers="body > table:nth-child(3) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(2) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(n+2)",
    visitorScoring="body > div > div.d50l > div.d25l > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(n+4)",
    homeScoring="body > div > div.d50r > div.d25l > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(n+4)",
    visitorPenalties="body > div > div.d50l > div.d25r > table:nth-child(1) > tbody:nth-child(1) > tr",
    homePenalties="body > div > div.d50r > div.d25r > table:nth-child(1) > tbody:nth-child(1) > tr",
    visitorShootout="body > div > div.d50l > div.d25l > table:nth-child(2) > tbody:nth-child(1) > tr:nth-child(n+4)",
    homeShootout="body > div > div.d50r > div.d25l > table:nth-child(2) > tbody:nth-child(1) > tr:nth-child(n+4)",
    # Selectors we'll use to verify that parsing other parts were correct.
    visitorGoals="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(7)",
    homeGoals="body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(3) > td:nth-child(7)",
)

columns = dict(
    Players=['number', 'position', 'name'],
    Penalties=['period', 'number', 'infraction', 'minutes', 'off_ice', 'start', 'end', 'on_ice'],
    Scoring=['period', 'time', 'extra', 'goal', 'assist1', 'assist2'],
    Shootout=['number', 'player', 'result'],
)

class NoGameStatsError(Exception):
    pass


def dedupe(headers):
    counts = {}
    cols = []
    for i, col in enumerate(headers):
        counts[col] = counts.get(col, 0) + 1
        if counts[col] > 1:
            col += str(counts[col])
        cols.append(col)
    return cols


def parse_td(td):
    if td.a:
        return {'text': td.a.text.strip(), 'link': td.a['href']}
    else:
        return td.text.strip()


def load_table(header_row):
    table = []
    if not header_row:
        return table
    columns = [t.text.strip() for t in header_row.find_all('th')]
    columns = dedupe(columns)
    row = header_row.next_sibling
    while row:
        tds = [parse_td(td) for td in row.find_all('td')]
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


def parse_td_rows(eles):
    val = []
    for ele in eles:
        if not ele.find('td'):
            continue
        val.append([i.text.strip() for i in ele.children])
    return val

@util.cache_json('seasons')
def get_seasons():
    soup = util.get_html(MAIN_STATS_URL, params={'league': '1'})
    season_ids = {o.text.strip(): int(o['value']) for o in soup.find('select')('option')}
    # Hack to use real season ID instead of "0" for current season.
    season_ids['Current'] = max(season_ids.values()) + 1
    return season_ids

def get_current_season():
    return get_seasons()['Current']

def _load_division(row):
    div_name = row.th.text.strip()[15:]
    # Get Div ID from next row.
    href = row.next_sibling.a['href'].strip()
    level_id = util.get_value_from_link(href, 'level')
    conference_id = util.get_value_from_link(href, 'conf')
    season_id = util.get_value_from_link(href, 'season')
    # Team stats table starts on next row.
    teams = []
    for team_row in load_table(row.next_sibling.next_sibling):
        team_a = team_row.pop('Team')
        team_row['name'] = team_a['text']
        team_row['id'] = util.get_value_from_link(team_a['link'], 'team')
        teams.append(team_row)
    return {'name': div_name, 'id': level_id, 'conference_id': conference_id, 'season_id': season_id, 'teams': teams}


# JSON helpers for REST API
@util.cache_json('division_stats', max_age=datetime.timedelta(hours=1))
def get_divisions(reload=False) -> list:
    soup = util.get_html(MAIN_STATS_URL, params={'league': '1'})
    divisions = []
    for row in soup.table.find_all('tr'):
        if not row.th:
            continue
        if row.th.text.startswith('Adult Division'):
            divisions.append(_load_division(row))
    return divisions


@util.cache_json('division/{div_id}#{conference_id}_players', max_age=datetime.timedelta(minutes=10))
def get_division_players(div_id: str, conference_id: str, season_id: str, reload=False):
    html = util.get_html(DIVISION_URL.format(
        division_id=div_id, conference_id=conference_id, season_id=season_id))
    player_table, goalie_table = pd.read_html(str(html), header=1)
    player_table.fillna('', inplace=True)
    goalie_table.fillna('', inplace=True)
    player_table.rename(columns={
        'Team': 'team',
        'Name': 'name', 
        '#': 'number', 
        'GP': 'games_played',
        'Ass.': 'assists',
        'Goals': 'goals',
        'Pts': 'points',
        'Pts/Game': 'ppg',
        'Hat': 'hat_tricks',
        'Min': 'penalty_minutes',
        }, inplace=True)
    goalie_table.rename(columns={
        'Team': 'team',
        'Name': 'name',
        'GP': 'games_played',
        'Shots': 'shots',
        'GA': 'goals_against',
        'GAA': 'goals_against_average',
        'Save %': 'save_percentage',
        'SO': 'shutouts',
        }, inplace=True)
    players, goalies = [], []
    for _, row in player_table.iterrows():
        players.append(row.to_dict())
    for _, row in goalie_table.iterrows():
        goalies.append(row.to_dict())
    return players, goalies


@util.cache_json('teams/{team_id}')
def get_team(team_id: int, **kwargs):
    info = {}
    soup = util.get_html(TEAM_URL.format(team_id=team_id, **kwargs))
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
        row = row.to_dict()
        if 'Goals.1' in row:
          row['away_goals'] = row.pop('Goals.1')
          row['home_goals'] = row.pop('Goals')
        row['id'] = int(row.pop('Game').replace('*', '').replace('^', ''))
        # lowercase keys are better.
        row = {k.lower(): v for k, v in row.items()}
        games.append(row)
    info['games'] = games
    return info

@util.cache_json('games/{game_id}', max_age=None)
def get_game_stats(game_id: int, reload=False):
    url = GAME_URL.format(game_id=game_id)
    soup = util.get_html(url)
    # TODO: Check if game has happened yet?
    if not soup.select_one(selectors['periodLength']).text.strip():
        raise NoGameStatsError()
    data = {}
    for name, selector in selectors.items():
        data[name] = []
        if name in ('date', 'time', 'league', 'level', 'location', 'scorekeeper', 'referee1', 'referee2', 'visitor', 'home', 'visitorGoals', 'homeGoals', 'periodLength'):
            ele = soup.select_one(selector)
            val = ele.text.strip()
            if ':' in val:
                val = val.split(':', 1)[1]
        elif name in ('homePlayers', 'visitorPlayers', 'homePenalties', 'visitorPenalties', 'homeScoring', 'visitorScoring', 'homeShootout', 'visitorShootout'):
            prefix = 'home' if 'home' in name else 'visitor'
            suffix = name.replace(prefix, '')
            eles = soup.select(selector)
            rows = parse_td_rows(eles)
            # Hack for players tables.
            if name in ('homePlayers', 'visitorPlayers'):
                rows = fix_players_rows(rows)
            keys = columns[suffix]
            val = [dict(zip(keys, row)) for row in rows]
        else:
            raise Exception('Unhandled section %s' % name)
        data[name] = val
    return data


def test():
    divs = get_divisions()
    div_players = {}
    for div in divs:
        print('Loading players for %s#%s' % (div['id'], div['conference_id']))
        div_players[div['id']] = get_division_players(div_id=div['id'], conference_id=div['conference_id'], season_id=div['season_id'])

    teams = []
    for div in divs:
        for team in div['teams']:
            print('Loading games for %s' % team['id'])
            teams.append(get_team(team_id=team['id']))
    for team in teams:
        for game in team['games']:
            game_time = util.parse_game_time(game['Date'], game['Time'])
            if game_time >= datetime.datetime.now():
                print('Skipping game in the future')
                continue
            print('Loading stats for %s' % game['id'])
            try:
                stats = get_game_stats(game_id=game['id'])
            except NoGameStatsError:
                pass

if __name__ == '__main__':
    if input('test all?') == 'y':
        test()
    pass
