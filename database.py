"""Wrapper class and utils for database."""

import datetime
import json
import sqlite3
from typing import Any


# Connect to the database (or create it if it doesn't exist)
class Database:
  """Wrapper class for Database."""

  def __init__(self):
    self._conn = sqlite3.connect("hockey_league.db")
    self._conn.execute("PRAGMA foreign_keys = 1")
    self._cursor = self._conn.cursor()

  def __del__(self):
    self._conn.close()

  def close(self):
    self._conn.close()

  def create_tables(self):
    """Create the Seasons table."""
    self._cursor.execute("""
    CREATE TABLE IF NOT EXISTS Seasons (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    )
    """)

    # Create the Divisions table
    self._cursor.execute("""
    CREATE TABLE IF NOT EXISTS Divisions (
        id INTEGER,
        conference_id INTEGER,
        name TEXT NOT NULL,
        PRIMARY KEY (id, conference_id)
    )
    """)

    self._cursor.execute("""
    CREATE TABLE IF NOT EXISTS Teams (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    )
    """)

    self._cursor.execute("""
    CREATE TABLE IF NOT EXISTS TeamStats (
        season_id INTEGER NOT NULL,
        division_id INTEGER NOT NULL,
        conference_id INTEGER NOT NULL,
        team_id INTEGER NOT NULL,
        stats TEXT NOT NULL,
        PRIMARY KEY (season_id, division_id, conference_id, team_id),
        FOREIGN KEY (division_id, conference_id)
          REFERENCES Divisions(id, conference_id),
        FOREIGN KEY (season_id) REFERENCES Seasons(id)
    )
    """)

    # Create the Games table
    self._cursor.execute("""
    CREATE TABLE IF NOT EXISTS Games (
        id INTEGER NOT NULL,
        season_id INTEGER NOT NULL,
        level TEXT NOT NULL,
        start_time TEXT NOT NULL,
        start_dt INTEGER NOT NULL,
        rink TEXT NOT NULL,
        home TEXT NOT NULL,
        away TEXT NOT NULL,
        home_id INTEGER,     
        away_id INTEGER,
        info TEXT,
        stats TEXT,
        PRIMARY KEY (id),
        FOREIGN KEY (season_id) REFERENCES Seasons(id)
    )
    """)

    # Commit the changes and close the connection
    self._conn.commit()

  def add_season(self, season_id: int, name: str):
    """Inserts season."""
    query = "INSERT OR REPLACE INTO SEASONS (id, name) VALUES (?, ?)"
    self._cursor.execute(query, (season_id, name))
    self._conn.commit()
    return self._cursor.lastrowid

  def add_division(
      self,
      division_id: int,
      conference_id: int,
      name: str,
  ):
    """Inserts division."""

    query = (
        "INSERT OR REPLACE INTO Divisions (id, conference_id, name)"
        " VALUES (?, ?, ?)"
    )

    self._cursor.execute(query, (division_id, conference_id, name))
    self._conn.commit()
    return self._cursor.lastrowid

  def add_team(
      self,
      team_id: int,
      name: str,
  ):
    """Inserts team."""
    # Always override team stats.
    query = (
        "INSERT OR REPLACE INTO Teams (id, name) VALUES (?, ?)"
    )

    self._cursor.execute(
        query,
        (team_id, name),
    )
    self._conn.commit()
    return self._cursor.lastrowid
  
  def set_team_stats(
      self,
      season_id: int,
      division_id: int,
      conference_id: int,
      team_id: int,
      stats: dict[str, Any],
  ):
    """Inserts team."""

    # Always override team stats.
    query = (
        "INSERT OR REPLACE INTO TeamStats (season_id, division_id,"
        " conference_id, team_id, stats) VALUES (?, ?, ?, ?, ?)"
    )

    try:
      self._cursor.execute(
          query,
          (
              season_id,
              division_id,
              conference_id,
              team_id,
              json.dumps(stats),
          ),
      )
    except Exception as e:
      raise Exception("Failed to add TeamStats (%s, %s, %s, %s): %s" % (team_id, season_id, division_id, conference_id, e))
    self._conn.commit()
    return self._cursor.lastrowid

  def add_game(
      self,
      game_id: int,
      season_id: int,
      level: str,
      start_dt: datetime.datetime,
      rink: str,
      home: str,
      home_id: int,
      away: str,
      away_id: int,
      **info: dict[str, Any],
  ):
    """Inserts game."""

    query = """
        INSERT OR REPLACE INTO Games (
            id,
            season_id,
            level,
            start_dt,
            rink,
            home,
            home_id,
            away,
            away_id,
            info
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    self._cursor.execute(
        query,
        (
            game_id,
            season_id,
            level,
            start_dt.timestamp() * 1000, # convert to micros
            rink,
            home,
            home_id,
            away,
            away_id,
            json.dumps(info),
        ),
    )
    self._conn.commit()
    return self._cursor.lastrowid

  def add_game_stats(self, game_id: int, stats: dict[str, Any]):
    """Inserts game stats."""

    # Always override game stats.
    query = "UPDATE OR REPLACE Games SET stats = ? WHERE id = ?"

    self._cursor.execute(query, (json.dumps(stats), game_id))
    self._conn.commit()
    return self._cursor.lastrowid

  # Helper methods
  def get_current_season(self):
    self._cursor.execute('''SELECT MAX(id) from Seasons''')
    return self._cursor.fetchone()[0]

  def list_season_divisions(self, season_id):
    self._cursor.execute("""
      SELECT DISTINCT
        s.id as season_id,
        s.name as season_name,
        d.id as division_id,
        d.conference_id,
        d.name as division_name,
        t.id as team_id,
        t.name as team_name
      FROM TeamStats as ts
        JOIN Divisions AS d ON (
          d.id = ts.division_id AND d.conference_id = ts.conference_id)
        JOIN Seasons AS s on ts.season_id = s.id
        JOIN Teams as t ON ts.team_id = t.id
        WHERE s.id = ?;""", (season_id, ))
    divisions = {}
    for row in self._cursor.fetchall():
      div_id = (row[2], row[3])
      if div_id not in divisions:
        divisions[div_id] = {
        'division_id': row[2],
        'conference_id': row[3],
        'name': row[4],
        'teams': []
        }
      divisions[div_id]['teams'].append({
        'team_id': row[5],
        'name': row[6]
      })
    divisions = list(divisions.values())
    # Sort by name and add season data.
    for i in range(len(divisions)):
      divisions[i]['teams'].sort(key=lambda a: a['name'])
    divisions.sort(key=lambda a: a['name'])
    return {
      'season_id': row[0],
      'season_name': row[1],
      'divisions': divisions,
    }
  
  def get_team_games(self, team_ids: list[int], min_season: int):
    games = []
    if not team_ids:
      return games
    team_ids = ",".join(map(str, team_ids))
    self._cursor.execute(f"""
    SELECT DISTINCT
      g.id,
      g.start_dt,
      g.rink,
      g.level,
      g.home,
      g.home_id,
      g.away,
      g.away_id
    FROM Games as g
      WHERE (
              g.home_id IN ({team_ids}) OR g.away_id IN ({team_ids})
      ) AND g.season_id >= {min_season};""")
    games = []
    keys = ['game_id',
            'start_time',
            'rink',
            'level',
            'home',
            'home_id',
            'away',
            'away_id',
            ]
    for row in self._cursor.fetchall():
      game = dict(zip(keys, row))
      games.append(game)
    return games

  def get_team_stats(self, team_ids: list[int], season_id: int):
    if not team_ids:
      print('NO TEAMS??')
      return []
    team_ids = ",".join(map(str, team_ids))
    print(team_ids)
    self._cursor.execute(f"""
    SELECT DISTINCT
      ts.team_id,
      t.name,
      s.name as season,
      s.id as season_id,
      d.name as level,
      ts.stats
    FROM TeamStats as ts
      JOIN Seasons s ON s.id = ts.season_id
      JOIN Teams t ON t.id = ts.team_id
      JOIN Divisions d ON (d.id = ts.division_id AND d.conference_id = ts.conference_id)
      WHERE ts.team_id IN ({team_ids}) AND ts.season_id = {season_id};""")
    teams = []
    keys = ['team_id',
            'name',
            'season',
            'season_id',
            'level',
            'stats',
            ]
    for row in self._cursor.fetchall():
      team = dict(zip(keys, row))
      team['stats'] = json.loads(team['stats'])
      teams.append(team)
    return teams

  # Helpers
  def ex(self, s: str):
    self._cursor.execute(s)
    if "select" in s.lower():
      return self._cursor.fetchall()
    self._conn.commit()

  def get_team_id(self, name: str, season_id: int):
    if not name:
      return -1
    self._cursor.execute('''
      SELECT
        id
      FROM Teams
      WHERE name = ?''', (name,))
    rows = self._cursor.fetchall()
    if len(rows) == 0:
      raise Exception("No team named %s" % name)
    if len(rows) == 1:
      return rows[0][0]
    # Choose the team with stats from the nearest season.
    ids = ','.join([str(r[0]) for r in rows])
    self._cursor.execute('SELECT team_id, season_id FROM TeamStats WHERE team_id IN (%s)' % ids)
    rows = self._cursor.fetchall()
    nearest = rows[0]
    for row in rows[1:]:
      if abs(row[1] - season_id) < abs(row[1] - nearest[1]):
        nearest = row
    return nearest[0]
    

if __name__ == "__main__":
  db = Database()
  db.create_tables()
  print("Database and tables created successfully!")
