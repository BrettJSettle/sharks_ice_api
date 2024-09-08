"""Scraper for SIAHL."""

import io
import re
from typing import Any

import database
import numpy as np
import pandas as pd
import util


TIMETOSCORE_URL = 'https://stats.sharksice.timetoscore.com/'
TEAM_URL = TIMETOSCORE_URL + 'display-schedule'
GAME_URL = TIMETOSCORE_URL + 'oss-scoresheet'
DIVISION_URL = TIMETOSCORE_URL + 'display-league-stats'
MAIN_STATS_URL = TIMETOSCORE_URL + 'display-stats.php'
CALENDAR = 'webcal://stats.sharksice.timetoscore.com/team-cal.php?team={team}&tlev=0&tseq=0&season={season}&format=iCal'

td_selectors = dict(
    # Game stats
    date=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(1) > td:nth-child(1)'
    ),
    time=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(1) > td:nth-child(2)'
    ),
    league=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(2) > td:nth-child(1)'
    ),
    level=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(3) > td:nth-child(1)'
    ),
    location=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(4) > td:nth-child(1)'
    ),
    scorekeeper=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(2) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(1) > td:nth-child(2)'
    ),
    periodLength=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(4) > td:nth-child(2)'
    ),
    referee1=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(2) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(2) > td:nth-child(2)'
    ),
    referee2=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(2) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(3) > td:nth-child(2)'
    ),
    away=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(2) > td:nth-child(2)'
    ),
    home=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(3) > td:nth-child(2)'
    ),
    # Selectors we'll use to verify that parsing other parts were correct.
    awayGoals=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(2) > td:nth-child(7)'
    ),
    homeGoals=(
        'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(3) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(3) > td:nth-child(7)'
    ),
)

tr_selectors = dict(
    awayPlayers=(
        'body > table:nth-child(3) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(1) > table:nth-child(2) > tbody:nth-child(1) >'
        ' tr:nth-child(2) > td:nth-child(1) > table:nth-child(1) >'
        ' tbody:nth-child(1) > tr:nth-child(n+2)'
    ),
    homePlayers=(
        'body > table:nth-child(3) > tbody:nth-child(1) > tr:nth-child(1) >'
        ' td:nth-child(2) > table:nth-child(1) > tbody:nth-child(1) >'
        ' tr:nth-child(2) > td:nth-child(1) > table:nth-child(1) >'
        ' tbody:nth-child(1) > tr:nth-child(n+2)'
    ),
    awayScoring=(
        'body > div > div.d50l > div.d25l > table:nth-child(1) >'
        ' tbody:nth-child(1) > tr:nth-child(n+4)'
    ),
    homeScoring=(
        'body > div > div.d50r > div.d25l > table:nth-child(1) >'
        ' tbody:nth-child(1) > tr:nth-child(n+4)'
    ),
    awayPenalties=(
        'body > div > div.d50l > div.d25r > table:nth-child(1) >'
        ' tbody:nth-child(1) > tr'
    ),
    homePenalties=(
        'body > div > div.d50r > div.d25r > table:nth-child(1) >'
        ' tbody:nth-child(1) > tr'
    ),
    awayShootout=(
        'body > div > div.d50l > div.d25l > table:nth-child(2) >'
        ' tbody:nth-child(1) > tr:nth-child(n+4)'
    ),
    homeShootout=(
        'body > div > div.d50r > div.d25l > table:nth-child(2) >'
        ' tbody:nth-child(1) > tr:nth-child(n+4)'
    ),
)

columns = dict(
    players=['number', 'position', 'name'],
    penalties=[
        'period',
        'number',
        'infraction',
        'minutes',
        'offIce',
        'start',
        'end',
        'onIce',
    ],
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
    'Game': ('id', lambda g: str(g).replace('*', '').replace('^', '')),
    'Date': 'date',
    'Time': 'time',
    'Rink': 'rink',
    'League': 'league',
    'Level': 'level',
    'Away': 'away',
    'Home': 'home',
    'Type': 'type',
    'Goals.1': 'homeGoals',
    'Goals': 'awayGoals',
    'Scoresheet': None,
    'Box Score': None,
    'Game Center': None,
}


class Error(Exception):
  pass


class MissingStatsError(Error):
  pass


def rename(initial: dict[str, str], mapping: dict[str, str]):
  """Renames columns in a dict."""
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


def parse_td_row(row):
  val = []
  for td in row('td'):
    if td('a'):
      val.append({'text': td.a.text.strip(), 'link': td.a['href']})
    else:
      val.append(td.text.strip())
  return val


def fix_players_rows(rows):
  val = []
  for row in rows:
    val.append(row[:3])
    if len(row) == 6:
      val.append(row[3:])
  return val


@util.cache_json('seasons')
def scrape_seasons():
  """Scrape season data from HTML."""
  soup = util.get_html(MAIN_STATS_URL, params={'league': '1'})
  season_ids = {
      o.text.strip(): int(o['value'])
      for o in soup.find('select')('option')
      if int(o['value']) > 0
  }
  current = 0
  for link in soup.find_all('a', href=True):
    current = re.search(r'season=(\d+)', link['href'])
    if current:
      current = int(current.group(1))
      break
  if current > 0:
    season_ids['Current'] = current
  return season_ids


def get_team_id(db: database.Database, team_name: str, season: int) -> str:
  """Get team id from string."""
  if not team_name:
    return None
  teams = db.list_teams('season_id = %s AND name = "%s"' % (season, team_name))
  # This shouldn't happen
  if len(teams) > 1:
    raise KeyError('Duplicate team names: %s' % teams)
  if not teams:
    raise ValueError('No team named %s in season %s' % (team_name, season))
  return teams[0]['team_id']


NO_LINK_INT = lambda a: int(a[0]) if a[0] else 0
NO_LINK = lambda a: a[0] if a[0] else ''

DIVISION_GAME_CONVERTERS = {
    'G': NO_LINK_INT,
    'GP': NO_LINK_INT,
    'W': NO_LINK_INT,
    'L': NO_LINK_INT,
    'T': NO_LINK_INT,
    'OTL': NO_LINK_INT,
    'PTS': NO_LINK_INT,
    'Streak': NO_LINK,
    'Tie Breaker': NO_LINK,
}


def _parse_division_teams(table_str: str):
  """Parse team data from a table."""
  table = pd.read_html(
      io.StringIO(table_str),
      extract_links='body',
      converters=DIVISION_GAME_CONVERTERS,
  )[0].fillna('')
  team = table['Team'].apply(pd.Series)
  table['id'] = team[1].str.extract(r'team=(\d+)')
  table['name'] = team[0]
  del table['Team']
  teams = []
  for _, row in table.iterrows():
    row = rename(row.to_dict(), team_columns_rename)
    teams.append(row)
  return teams


def scrape_season_divisions(season_id: int):
  """Scrape divisions and teams in a season."""
  soup = util.get_html(MAIN_STATS_URL, params=dict(league=1, season=season_id))
  divisions = []
  division_name = ''
  division_id = 0
  conference_id = 0
  table_rows = []
  for row in soup.table.find_all('tr'):
    # Ignore non-header rows
    if row('th'):
      header = row.th.text.strip()
      if header.startswith('Adult Division') or header.startswith('Senior'):
        division_name = header
        href = row.next_sibling.a['href'].strip()
        division_id = int(util.get_value_from_link(href, 'level'))
        conference_id = int(util.get_value_from_link(href, 'conf'))
        continue
      if len(table_rows) > 1:
        teams = _parse_division_teams(
            '<table>' + '\n'.join(table_rows) + '</table>'
        )
        divisions.append({
            'name': division_name,
            'id': division_id,
            'conferenceId': conference_id,
            'seasonId': season_id,
            'teams': teams,
        })
      table_rows = [str(row)]
    else:
      table_rows.append(str(row))

  # Add the last division too.
  if len(table_rows) > 1:
    teams = _parse_division_teams(
        '<table>' + '\n'.join(table_rows) + '</table>'
    )
    divisions.append({
        'name': division_name,
        'id': division_id,
        'conferenceId': conference_id,
        'seasonId': season_id,
        'teams': teams,
    })
  return divisions


@util.cache_json('seasons/{season_id}/teams/{team_id}')
def get_team(season_id: int, team_id: int, reload=False):
  """Get team info from a season and id."""
  info = {}
  soup = util.get_html(TEAM_URL, params=dict(season=season_id, team=team_id))
  if not soup.table:
    return {}

  games = []
  results = pd.read_html(io.StringIO(str(soup.table)), header=1)[0]
  results = results.fillna(np.nan).replace([np.nan], [None])
  for _, row in results.iterrows():
    row = rename(row.to_dict(), game_columns_rename)
    if row['type'] == 'Practice':
      continue
    date = row.pop('date', None)
    time = row.pop('time', None)
    year = None  # Estimate year
    if not date or not time:
      row['start_time'] = None
    else:
      row['start_time'] = util.parse_game_time(date, time, year)
    # Goals can be str, int, or float for some reason.
    # Correct all to string to allow for shootouts (e.g. "4 S")
    if isinstance(row['homeGoals'], float):
      row['homeGoals'] = str(int(row['homeGoals']))
    elif row['homeGoals'] is None:
      del row['homeGoals']
    if isinstance(row['awayGoals'], float):
      row['awayGoals'] = str(int(row['awayGoals']))
    elif row['awayGoals'] is None:
      del row['awayGoals']
    games.append(row)
  info['games'] = games
  return info


def scrape_game_stats(game_id: int):
  """Get game stats from an id."""
  soup = util.get_html(GAME_URL, params=dict(game_id=game_id))
  if not soup.select_one(td_selectors['periodLength']):
    raise MissingStatsError('No game stats for %s' % game_id)
  data = {}
  for name, selector in td_selectors.items():
    ele = soup.select_one(selector)
    if not ele and name == 'scorekeeper':
      raise MissingStatsError(
          'Failed to read data for game. Has it happened yet?'
      )
    val = ele.text.strip()
    if ':' in val:
      val = val.split(':', 1)[1]
    data[name] = val

  for name, selector in tr_selectors.items():
    prefix = 'home' if name.startswith('home') else 'away'
    suffix = name[len(prefix) :].lower()
    eles = soup.select(selector)
    rows = [parse_td_row(row) for row in eles if row('td')]
    # Hack for players tables.
    if name.endswith('Players'):
      rows = fix_players_rows(rows)
    val = [dict(zip(columns[suffix], row)) for row in rows]
    data[name] = val
  return data


def sync_seasons(db: database.Database):
  seasons = scrape_seasons()
  for name, season_id in seasons.items():
    db.add_season(season_id, name)
  if 'Current' not in seasons:
    db.add_season(0, 'Current')


def sync_divisions(db: database.Database, season: int):
  """Sync divisions from site."""
  divs = scrape_season_divisions(season_id=season)
  print('Found %d divisions in season %s...' % (len(divs), season))
  for div in divs:
    db.add_division(
        division_id=div['id'],
        conference_id=div['conferenceId'],
        name=div['name'],
    )
    print('%s teams in %s' % (len(div['teams']), div['name']))
    for team in div['teams']:
      team_id = team.pop('id')
      team_name = team.pop('name')
      db.add_team(
          season_id=season,
          division_id=div['id'],
          conference_id=div['conferenceId'],
          team_id=team_id,
          name=team_name,
          stats=team,
      )


def get_team_or_unknown(db: database.Database, team_name: str, season: int):
  """Get team id from string."""
  try:
    team_id = get_team_id(db, team_name, season)
  except ValueError as e:
    print(e)
    db.add_season(season_id=-1, name='UNKNOWN')
    db.add_division(division_id=-1, conference_id=-1, name='UNKNOWN')
    team_id = -1
    db.add_team(
        season_id=-1,
        division_id=-1,
        conference_id=-1,
        team_id=team_id,
        name='UNKNOWN',
        stats={},
    )
  return team_id


def add_game(
    db: database.Database,
    season: int,
    team: dict[str, Any],
    game: dict[str, Any],
):
  """Add a game to the database."""
  # Clean up dict and translate data.
  game_id = game.pop('id')
  start_time = game.pop('start_time', None)
  rink = game.pop('rink', None)
  # Get Team IDs from names and season.
  home, away = game['home'], game['away']
  if home == team['name']:
    home_id = team['team_id']
    away_id = get_team_or_unknown(db, away, season)
  else:
    home_id = get_team_or_unknown(db, home, season)
    away_id = team['team_id']
  db.add_game(
      season_id=season,
      division_id=team['division_id'],
      conference_id=team['conference_id'],
      game_id=game_id,
      home_id=home_id,
      away_id=away_id,
      rink=rink,
      start_time=start_time,
      info=game,
  )


def sync_season_teams(db: database.Database, season: int):
  """Sync games from site."""
  teams = db.list_teams('season_id = %d' % season)
  game_ids = set()
  for team in teams:
    print('Syncing %s season %d...' % (team['name'], season))
    team_info = get_team(season_id=season, team_id=team['team_id'])
    games = team_info.pop('games', [])
    for game in games:
      if game['id'] in game_ids:
        continue
      game_ids.add(game['id'])
      add_game(db, season, team, game)


def sync_game_stats(db: database.Database):
  games = db.list_games()
  for game in games:
    if not game['stats']:
      try:
        stats = scrape_game_stats(game['game_id'])
      except Exception as e:
        print(e)
        continue
      db.add_game_stats(game['game_id'], stats)


def load_data(db: database.Database):
  db.create_tables()
  sync_seasons(db)
  # print(db.list_seasons())
  seasons = [a['season_id'] for a in db.list_seasons()]
  for season in sorted(seasons, reverse=True):
    if season >= 32:
      continue
    sync_divisions(db, season)
    sync_season_teams(db, season)


DATABASE = database.Database()

if __name__ == '__main__':
  load_data(DATABASE)
  # d = scrape_season_divisions(66)
