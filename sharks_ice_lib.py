import requests
from bs4 import BeautifulSoup
from collections import namedtuple
import datetime
from urllib import parse

TIMETOSCORE_URL = 'https://stats.sharksice.timetoscore.com/'
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
          divisions[division][name] = Team(name, division, link)
  return divisions


class Team(object):
  def __init__(self, name, division, link):
    self.name = name
    self.division = division
    self.link = link
    self.games = []

  def load_games(self):
    print('Loading games for %s' % self)
    games = []
    soup = get_html(self.link)
    header = soup.table.tr
    while header.next_sibling.th:
      header = header.next_sibling
    for game in load_table(header):
      start_time = game['Date'].text.strip() + ' ' + game['Time'].text.strip()
      year = str(datetime.datetime.now().year)
      start_time = datetime.datetime.strptime(year + ' ' + start_time, '%Y %a %b %d %I:%M %p')
      rink = game['Rink'].text.strip()
      home = game['Home'].text.strip()
      away = game['Away'].text.strip()
      link = None
      if game['Game'].a:
        link = TIMETOSCORE_URL + game['Game'].a['href']
      g = Game(start_time, rink, home, away, link)
      games.append(g)
    self.games = games
    return games

  def __str__(self):
    return '%s in %s' % (self.name, self.division)

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

def _load_goals(game, team, header, player_map={}):
  goals = []
  for goal in load_table(header):
    ts = goal['Time'].text.strip()
    if ':' not in ts:
      ts = '0:' + ts
    m, s = map(float, ts.split(':'))
    timestamp = datetime.timedelta(minutes=m, seconds=s)
    player = goal['Goal'].text.strip()
    player = player_map.get(player, '#' + player)
    goals.append(Goal(
      game=game,
      team=team,
      period=int(goal['Per'].text.strip()),
      time=timestamp,
      player=player))
    return goals

class Game(object):
  def __init__(self, start_time, rink, home, away, link):
    self.start_time = start_time
    self.rink = rink
    self.home = home
    self.away = away
    self.link = link
    self.goals = []

  def load_game_scoresheet(self):
    if not self.link:
      return
    print('Loading scoresheet for %s' % self)
    goals = []
    soup = get_html(self.link)
    players = {}
    away_team_header, home_team_header = [
        h for h in soup.find_all('th')
        if 'players in game' in h.text.lower()
        ]
    away_players = _load_players(away_team_header.find_parent('table').table.tr)
    home_players = _load_players(home_team_header.find_parent('table').table.tr)

    headers = soup.find_all('th', text='Scoring')
    if len(headers) != 2:
      raise Exception('Expected 2 headers with text="Scoring", found %d at %s' % len(headers), url)
    away_score_header = headers[0].find_parent('table').find_all('tr')[2]
    home_score_header = headers[1].find_parent('table').find_all('tr')[2]
    goals.extend(_load_goals(self, self.away, away_score_header, away_players))
    goals.extend(_load_goals(self, self.home, home_score_header, home_players))
    self.goals = goals
    return goals

  def __str__(self):
    start = datetime.datetime.strftime(self.start_time, '%c')
    return '%s on %s: %s(H) vs %s(A)' % (start, self.rink, self.home, self.away)


class Goal(object):
  def __init__(self, game, team, period, time, player):
    self.game = game
    self.team = team
    self.period = period
    self.time = time
    self.player = player

  def _estimate_time(self):
    estimate = self.game.start_time
    estimate += datetime.timedelta(minutes=5)  # warmups
    period_minutes = datetime.timedelta(minutes=22)  # estimate periods at 22m
    estimate += period_minutes * (self.period - 1)
    estimate += (period_minutes - self.time)  # Time is time remaining in period
    return estimate

  def print_livebarn_link(self):
    estimated_time = self._estimate_time()
    link = get_livebarn_url(estimated_time, self.game.rink)
    print('''Generating livebarn link for %s...
Estimated time is %s on %s rink
1. Open https://livebarn.com/en/signin and login
2. Copy the following URL to the address bar
%s''' % (self, datetime.datetime.strftime(estimated_time, '%c'), self.game.rink, link))

    def __str__(self):
      return 'Period %s at %s: %s goal by %s' % (self.period, self.time, self.team, self.player)


# JSON helpers for REST API
def load_divisions_json():
  divisions = load_divisions()
  json = {}
  for div, teams in divisions.items():
    json[div] = []
    for team in teams.values():
      team_id = dict(parse.parse_qsl(parse.urlsplit(team.link).query))['team']
      json[div].append({'name': team.name, 'team_id': team_id})
  return json

def load_team_json(team_id):
  games = {}
  soup = get_html(('https://stats.sharksice.timetoscore.com/display-schedule?'
    'team={team_id}').format(team_id=team_id))
  header = soup.table.tr
  while header.next_sibling.th:
    header = header.next_sibling
  for game in load_table(header):
    game_id = game['Game'].text.strip().replace('*', '')
    start_time = game['Date'].text.strip() + ' ' + game['Time'].text.strip()
    year = str(datetime.datetime.now().year)
    start_time = datetime.datetime.strptime(year + ' ' + start_time, '%Y %a %b %d %I:%M %p')
    rink = game['Rink'].text.strip()
    home = game['Home'].text.strip()
    away = game['Away'].text.strip()
    away_goals = game['Goals'].text.strip()
    home_goals = game['Goals2'].text.strip()
    link = None
    if game['Game'].a:
      link = TIMETOSCORE_URL + game['Game'].a['href']
    g = Game(start_time, rink, home, away, link)
    games[game_id] = {
        'start_time': start_time,
        'rink': rink,
        'home': home,
        'home_goals': home_goals,
        'away': away,
        'away_goals': away_goals}
  return games

def load_game_json(game_id):
  url = 'https://stats.sharksice.timetoscore.com/oss-scoresheet?game_id={game_id}'
  events = {'goals': [], 'penalties': []}
  soup = get_html(url.format(game_id=game_id))
  players = {}
  away_team_header, home_team_header = [
      h for h in soup.find_all('th')
      if 'players in game' in h.text.lower()
      ]
  away_players = _load_players(away_team_header.find_parent('table').table.tr)
  home_players = _load_players(home_team_header.find_parent('table').table.tr)

  # TODO: Team names include values from other cells. Fix this.
  away = soup.find_all('th', text='Visitor')[0].next_sibling.text.strip()
  home = soup.find_all('th', text='Home')[0].next_sibling.text.strip()

  headers = soup.find_all('th', text='Scoring')
  if len(headers) != 2:
    raise Exception('Expected 2 headers with text="Scoring", found %d at %s' % len(headers), url)
  away_score_header = headers[0].find_parent('table').find_all('tr')[2]
  home_score_header = headers[1].find_parent('table').find_all('tr')[2]
  events['goals'].extend(_load_goals_json(away, away_score_header, away_players))
  events['goals'].extend(_load_goals_json(home, home_score_header, home_players))
  return events

def _load_goals_json(team, header, player_map={}):
  goals = []
  for goal in load_table(header):
    ts = goal['Time'].text.strip()
    if ':' not in ts:
      ts = '0:' + ts
    m, s = map(float, ts.split(':'))
    timestamp = datetime.timedelta(minutes=m, seconds=s)
    player = goal['Goal'].text.strip()
    player = player_map.get(player, '#' + player)
    goals.append({
      'team': team,
      'period': int(goal['Per'].text.strip()),
      'seconds_remaining': timestamp.seconds,
      'player': player})
    return goals
