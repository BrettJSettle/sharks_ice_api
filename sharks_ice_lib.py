import requests
from bs4 import BeautifulSoup
from collections import namedtuple
import datetime
from urllib import parse

TIMETOSCORE_URL = 'https://stats.sharksice.timetoscore.com/'
TEAM_URL = 'https://stats.sharksice.timetoscore.com/display-schedule?team={team_id}'
GAME_URL = 'https://stats.sharksice.timetoscore.com/oss-scoresheet?game_id={game_id}'
MAIN_STATS_URL = TIMETOSCORE_URL + 'display-stats.php'

LIVEBARN_RINKS = {
    'San Jose South': 547,
    'San Jose North': 546,
    'San Jose East': 548,
    'San Jose Center': 549,
    }
LIVEBARN_URL = 'https://livebarn.com/en/videov/?begindate={date}&sid={sid}'


def get_livebarn_url(date, rink):
  sid = LIVEBARN_RINKS[rink]
  if date.minute % 30 != 0:
    date -= datetime.timedelta(minutes=date.minute % 30)
  date = datetime.datetime.strftime(date, '%Y-%m-%dT%H:%M')
  return LIVEBARN_URL.format(date=date, sid=sid)


def get_html(url, params={}):
  r = requests.get(url, params=params)
  return BeautifulSoup(r.text, 'html.parser')


def dedupe(headers):
  counts = {}
  cols = []
  for i, col in enumerate(headers):
    counts[col] = counts.get(col, 0) + 1
    if counts[col] > 1:
      col += str(counts[col])
    cols.append(col)
  return cols


def load_table(header_row):
  table = []
  if not header_row:
    return table
  columns = [t.text.strip() for t in header_row.find_all('th')]
  columns = dedupe(columns)
  row = header_row.next_sibling
  while row:
    cols = row.find_all('td')
    if len(cols) <= 1:
      break
    table.append(dict(zip(columns, cols)))
    row = row.next_sibling
  return table


def _estimate_time(start_time, period, seconds_remaining):
  estimate = start_time
  estimate += datetime.timedelta(minutes=5)  # warmups
  period_minutes = datetime.timedelta(minutes=22)  # estimate periods at 22m
  estimate += period_minutes * (period - 1)
  estimate += (period_minutes - seconds_remaining)  # Time is time remaining in period
  return estimate


def get_team_id_from_link(url):
  query = parse.urlsplit(url).query
  query_map = dict(parse.parse_qsl(query))
  return query_map.get('team')

# JSON helpers for REST API
def load_divisions():
  soup = get_html(MAIN_STATS_URL, params={'league': '1'})
  divisions = {}
  division = None
  for row in soup.table.find_all('tr'):
    if row.th:
      if row.th.text.startswith('Adult Division'):
        division = row.th.text.strip()[15:]
        divisions[division] = {}
      elif row.th.text == 'Team':
        for team_row in load_table(row):
          name = team_row['Team'].text.strip()
          link = TIMETOSCORE_URL + team_row['Team'].a['href']
          team_id = get_team_id_from_link(link)
          divisions[division][name] = {'name': name, 'team_id': team_id}
  return divisions

def parse_date_time(date_str, time_str):
  year = str(datetime.datetime.now().year)
  return datetime.datetime.strptime(year + ' ' + date_str + ' ' + time_str, '%Y %a %b %d %I:%M %p')

def load_team(team_id: int):
  games = {}
  soup = get_html(TEAM_URL.format(team_id=team_id))
  if not soup.table:
    return {}
  header = soup.table.tr
  while header.next_sibling and header.next_sibling.th:
    header = header.next_sibling
  for game in load_table(header):
    game_id = game['Game'].text.strip().replace('*', '')
    start_time = parse_date_time(game['Date'].text.strip(), game['Time'].text.strip())
    rink = game['Rink'].text.strip()
    home = game['Home'].text.strip()
    away = game['Away'].text.strip()
    games[game_id] = {
        'start_time': start_time,
        'rink': rink,
        'home': home,
        'away': away}
    if game['Goals'].text.strip():
      games[game_id]['away_goals'] = game['Goals'].text.strip()
    if game['Goals2'].text.strip():
      games[game_id]['home_goals'] = game['Goals2'].text.strip()
  return games


def _load_players(header):
  players = {}
  for row in load_table(header):
    jersey = row['#'].text.strip()
    name = row['Name'].text.strip().title()
    players[jersey] = name
    if '#2' in row and 'Name2' in row:
      jersey = row['#2'].text.strip()
      name = row['Name2'].text.strip().title()
      players[jersey] = name
  return players


def _get_offset_row(th, offset=1):
  parent_table = th.find_parent('table')
  rows = parent_table.find_all('tr')
  if len(rows) <= offset:
    return None
  return rows[offset]


def load_game(game_id):
  soup = get_html(GAME_URL.format(game_id=game_id))
  events = {'goals': [], 'penalties': []}
  players = {}
  team_players_headers = []
  scoring_headers = []
  penalties_headers = []
  away, home = '', ''
  for th in soup.find_all('th'):
    if 'players in game' in th.text.lower():
      parent_table = th.find_parent('table')
      if parent_table and parent_table.table and parent_table.table.tr:
        row = th.find_parent('table').table.tr
        team_players_headers.append(row)
    elif th.text.strip() == 'Visitor':
      away = th.next_sibling.text.strip()
    elif th.text.strip() == 'Home':
      home = th.next_sibling.text.strip()
    elif th.text.strip() == 'Scoring':
      scoring_headers.append(_get_offset_row(th, 2))
    elif th.text.strip() == 'Penalties':
      penalties_headers.append(_get_offset_row(th, 1))

  if len(team_players_headers) != 2 or len(scoring_headers) != 2:
    return {'error': 'Failed to find player and goal information for both teams.'}

  away_players = _load_players(team_players_headers[0])
  home_players = _load_players(team_players_headers[1])

  events['goals'].extend(_load_goals(away, scoring_headers[0], away_players))
  events['goals'].extend(_load_goals(home, scoring_headers[1], home_players))
  events['penalties'].extend(_load_penalties(away, penalties_headers[0], away_players))
  events['penalties'].extend(_load_penalties(home, penalties_headers[1], home_players))
  return events


def _load_goals(team, header, player_map={}):
  goals = []
  for goal in load_table(header):
    player = goal['Goal'].text.strip()
    player = player_map.get(player, '#' + player)
    goals.append({
      'team': team,
      'period': int(goal['Per'].text.strip()),
      'time': goal['Time'].text.strip(),
      'player': player})
  return goals

def _load_penalties(team, header, player_map={}):
  penalties = []
  for penalty in load_table(header):
    if not penalty:
      continue
    player = penalty['#'].text.strip()
    player = player_map.get(player, '#' + player)
    penalties.append({
      'team': team,
      'period': int(penalty['Per'].text.strip()),
      'start_time': penalty['Start'].text.strip(),
      'off_ice_time': penalty['Off Ice'].text.strip(),
      'end_time': penalty['End'].text.strip(),
      'infraction': penalty['Infraction'].text.strip(),
      'minutes': penalty['Min'].text.strip(),
      'player': player})
  return penalties
