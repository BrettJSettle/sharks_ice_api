"""Scraper for SIAHL."""

from typing import Any
import time
import io
import datetime
import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import database
import util

TIMETOSCORE_URL = 'https://stats.sharksice.timetoscore.com/'
TEAM_URL = TIMETOSCORE_URL + 'display-schedule'
GAME_URL = TIMETOSCORE_URL + 'oss-scoresheet'
DIVISION_URL = TIMETOSCORE_URL + 'display-league-stats'
MAIN_STATS_URL = TIMETOSCORE_URL + 'display-stats.php'
CALENDAR = 'webcal://stats.sharksice.timetoscore.com/team-cal.php?team={team}&tlev=0&tseq=0&season={season}&format=iCal'

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
  level = ''
  division_id = 0
  conference_id = 0
  table_rows = []
  for row in soup.table.find_all('tr'):
    # Non-header rows are teams
    if not row('th'):
      table_rows.append(str(row))
      continue

    # Parse level of past N rows.
    if len(table_rows) > 1:
      divisions.append({
          'name': level,
          'id': division_id,
          'conference_id': conference_id,
          'season_id': season_id,
          'teams': _parse_division_teams('<table>' + '\n'.join(table_rows) + '</table>')
      })
    # Start parsing a new header.
    header = row.th.text.strip()
    if header.startswith('Adult Division') or header.startswith('Senior'):
      level = header
      div_stats_link = row.next_sibling.a['href'].strip()
      division_id = int(util.get_value_from_link(div_stats_link, 'level'))
      conference_id = int(util.get_value_from_link(div_stats_link, 'conf'))
    table_rows = [str(row)]

  # Add the last division too.
  if len(table_rows) > 1:
    divisions.append({
        'name': level,
        'id': division_id,
        'conference_id': conference_id,
        'season_id': season_id,
        'teams': _parse_division_teams('<table>' + '\n'.join(table_rows) + '</table>'),
    })
  return divisions

class DumbDateTime:
  MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  def __init__(self, month, day, hour, minute):
    self._month = month
    self._day = day
    self._hour = hour
    self._minute = minute

  @staticmethod
  def from_string(s: str):
    md, hm = s.split()
    m, d = md.split('/')
    h, mi = hm.split(':')
    return DumbDateTime(m, d, h, mi)

  @staticmethod
  def from_date_time(date: str, timeofday: str):
    timeofday = timeofday.replace('12 Noon', '12:00 PM')
    try:
      _, month, day = date.split()
      hour_minute, m = timeofday.split()
      hour, minute = hour_minute.split(':')
      hour = int(hour)
      if m == 'PM' and hour < 12:
        hour += 12
    except ValueError as e:
      raise Exception("Failed to parse %s %s to datetime" % (date, timeofday))
    return DumbDateTime(
      month=(DumbDateTime.MONTHS.index(month) + 1),
      day=int(day), 
      hour=hour,
      minute=int(minute))

  def __str__(self):
    return '%d/%d %d:%02d' % (self._month, self._day, self._hour, self._minute)
  
  def as_date(self, year: int):
    return datetime.datetime(year=year, month=self._month, day=self._day, hour=self._hour, minute=self._minute)

def ordinal(n):
  """Converts an integer to its ordinal string (e.g., 1st, 2nd, 3rd)."""

  if 11 <= (n % 100) <= 13:
    return f"{n}th"
  else:
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def get_game_dt(game_id: int):
  soup = util.get_html(GAME_URL, params=dict(game_id=game_id))
  start_path =(
    'body > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) >'
    ' td:nth-child(1) > table:nth-child(1) > tbody:nth-child(1) >'
    ' tr:nth-child(1) > td:nth-child(1)')
  start_ele = soup.select_one(start_path)
  val = start_ele.text.strip().replace('Date:', '')
  dt = datetime.datetime.strptime(val, '%m-%d-%y')
  return dt

def guess_year(start_time: DumbDateTime, first_game_dt: datetime.datetime) -> datetime.datetime:
  try:
    same_year = start_time.as_date(first_game_dt.year)
  except:
    # Usually means leap year
    return start_time.as_date(first_game_dt.year + 1)
  if (same_year < first_game_dt):
    return start_time.as_date(first_game_dt.year + 1)
  return same_year

# Class for syncing data from scrapers and adding to DB
class Syncer:
  def __init__(self, db: database.Database):
    self._db = db
    self._min_season = 0

  def get_season_games(self, driver, season_id: int):
    url = 'https://stats.sharksice.timetoscore.com/display-schedule.php?stat_class=1&league=1&season=%s' % season_id
    driver.get(url)
    # Wait for the page to load (adjust the timeout as needed)
    wait = WebDriverWait(driver, 5)
    try:
      wait.until(EC.presence_of_element_located((By.TAG_NAME, 'tbody')))
    except:
      return []

    # Get the HTML content of the table
    html_content = driver.page_source
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')

    # Extract data from the table (adjust the selectors as needed)
    column_rename = {
      'Game': 'game_id',
      'Date': 'date',
      'Time': 'time',
      'Rink': 'rink',
      'League': 'league',
      'Level': 'level',
      'Away': 'away',
      # 'away_goals', 
      'Home': 'home', 
      # 'home_goals', 
      'Type': 'type', 
    }
    rows = table.find_all('tr')
    # Parse headers
    columns = []
    for h in rows[1].find_all('th'):
      text = h.text.strip()
      if text == 'Goals':
        text = 'away_goals' if 'away_goals' not in columns else 'home_goals'
      text = column_rename.get(text, text)
      columns.append(text)
    
    first_game_dt = None
    for row in rows[2:]:
      cells = row.find_all('td')
      row_data = [cell.text.strip() for cell in cells]
      row_data = [a.replace('  ', ' ') for a in row_data]
      if len(cells) != len(columns):
        print('Row has %s, Columns is %s' % (len(cells), len(columns)))
        continue
      game = dict(zip(columns, row_data))
      if game['type'] == 'Practice':
        continue
      if not game['away'] and not game['home']:
        continue
      game['rink'] = game['rink'].replace('San Jose ', '')
      game['level'] = game['level'].replace('Adult Division', 'Div')
      # Use first game time to estimate year for all games.
      if first_game_dt is None:
        first_game_dt = get_game_dt(game['game_id'])
      start_time = DumbDateTime.from_date_time(game.pop('date'), game.pop('time'))
      game['start_dt'] = guess_year(start_time, first_game_dt)
      yield game

  def sync_season_teams(self, season_id: int):
    """Sync divisions from site."""
    print('Scraping divisions from season %s' % season_id)
    divs = scrape_season_divisions(season_id=season_id)
    if len(divs) == 0:
      raise Exception("No divs found for season %s" % season_id)
    for div in divs:
      self._db.add_division(
          division_id=div['id'],
          conference_id=div['conference_id'],
          name=div['name'],
      )
      for i, team in enumerate(div['teams']):
        team_id = team.pop('id')
        team_name = team.pop('name')
        self._db.add_team(
            team_id=team_id,
            name=team_name,
        )
        team['place'] = ordinal(i + 1)
        self._db.set_team_stats(
            season_id=season_id,
            division_id=div['id'],
            conference_id=div['conference_id'],
            team_id=team_id,
            stats=team,
        )

  def sync_season_games(self, season_id: int):
    print('Scraping games from season %s' % season_id)
    num_games = 0
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    try:
      for game in self.get_season_games(driver, season_id):
        # Goals can be str, int, or float for some reason.
        # Correct all to string to allow for shootouts (e.g. "4 S")
        if isinstance(game['home_goals'], float):
          game['home_goals'] = str(int(game['home_goals']))
        elif game['home_goals'] is None:
          del game['home_goals']
        if isinstance(game['away_goals'], float):
          game['away_goals'] = str(int(game['away_goals']))
        elif game['away_goals'] is None:
          del game['away_goals']
        
        game['game_id'] = game['game_id'].replace('*', '').replace('^', '')

        try:
          game['home_id'] = self._db.get_team_id(game['home'], season_id=season_id)
        except Exception as e:
          print("Failed to get teams for game %s: %s" % (game['game_id'], e))
          game['home_id'] = -1

        try:
          game['away_id'] = self._db.get_team_id(game['away'], season_id=season_id)
        except Exception as e:
          print("Failed to get teams for game %s: %s" % (game['game_id'], e))
          game['away_id'] = -1
        self._db.add_game(
          season_id=season_id,
          **game)
        num_games += 1
    finally:
      driver.close()
    return num_games

  def set_min_season(self, min_season):
    self._min_season = min_season
    
  def sync(self, lookback=datetime.timedelta(days=1)):
    season_id = self._min_season
    season_errors = 0
    while True:
      if season_errors >= 4:
        break
      try:
        self.sync_season_teams(season_id=season_id)
      except Exception:
        season_errors += 1
        season_id += 1
        continue
      games = self.sync_season_games(season_id=season_id, lookback=lookback)
      print('Scraped %d games in season %d' % (games, season_id))
      # TODO: Move min_season if current season is invalid or too far back.
      season_errors = 0
      season_id += 1


def scrape():
  DATABASE.create_tables()
  syncer = Syncer(DATABASE)
  syncer.set_min_season(60)
  while True:
    syncer.sync()
    time.sleep(10)


DATABASE = database.Database()

if __name__ == '__main__':
  # scrape()
  pass
