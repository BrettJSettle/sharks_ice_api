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

  def create_tables(self):
    """Create the Seasons table."""
    self._cursor.execute("""
    CREATE TABLE IF NOT EXISTS Seasons (
        season_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    )
    """)

    # Create the Divisions table
    self._cursor.execute("""
    CREATE TABLE IF NOT EXISTS Divisions (
        division_id INTEGER,
        conference_id INTEGER,
        name TEXT NOT NULL,
        PRIMARY KEY (division_id, conference_id)
    )
    """)

    self._cursor.execute("""
    CREATE TABLE IF NOT EXISTS Teams (
        season_id INTEGER NOT NULL,
        division_id INTEGER NOT NULL,
        conference_id INTEGER NOT NULL,
        team_id INTEGER,
        name TEXT NOT NULL,
        stats TEXT NOT NULL,
        PRIMARY KEY (season_id, division_id, conference_id, team_id),
        FOREIGN KEY (division_id, conference_id)
          REFERENCES Divisions(division_id, conference_id),
        FOREIGN KEY (season_id) REFERENCES Seasons(season_id)
    )
    """)

    # Create the Players table
    self._cursor.execute("""
    CREATE TABLE IF NOT EXISTS Players (
        player_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        info TEXT NOT NULL
    )
    """)

    # Create the Games table
    self._cursor.execute("""
    CREATE TABLE IF NOT EXISTS Games (
        season_id INTEGER NOT NULL,
        division_id INTEGER NOT NULL,
        conference_id INTEGER NOT NULL,
        game_id INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        rink TEXT NOT NULL,
        homeId INTEGER,
        awayId INTEGER,
        info TEXT,
        stats TEXT,
        PRIMARY KEY (game_id),
        FOREIGN KEY (season_id) REFERENCES Seasons(season_id),
        FOREIGN KEY (division_id, conference_id)
          REFERENCES Divisions(division_id, conference_id)
    )
    """)

    # Commit the changes and close the connection
    self._conn.commit()

  # Get methods

  def get_season(self, season_id: int):
    seasons = self.list_seasons(f"season_id = {season_id}")
    return seasons[0] if seasons else None

  def get_division(self, division_id: int, conference_id: int):
    divs = self.list_divisions(
        f"division_id = {division_id} AND conference_id = {conference_id}"
    )
    return divs[0] if divs else None

  def get_team(
      self, season_id: int, division_id: int, conference_id: int, team_id: int
  ):
    """Get a team from identifiers."""
    teams = self.list_teams(
        f"season_id = {season_id} and division_id = {division_id} and"
        f" conference_id = {conference_id} and team_id = {team_id}"
    )
    return teams[0] if teams else None

  def get_player(self, player_id: int):
    players = self.list_players(f"player_id = {player_id}")
    return players[0] if players else None

  def get_game(self, game_id: int):
    games = self.list_games(f"game_id = {game_id}")
    return games[0] if games else None

  # List methods

  def list_seasons(self, conditions: str = "", *args):
    if conditions:
      conditions = " WHERE " + conditions
    keys = ["season_id", "name"]
    cols = ", ".join(keys)
    self._cursor.execute(f"SELECT {cols} FROM Seasons{conditions}", args)
    return [dict(zip(keys, row)) for row in self._cursor.fetchall()]

  def list_divisions(self, conditions: str = "", *args):
    if conditions:
      conditions = " WHERE " + conditions
    keys = ["division_id", "conference_id", "name"]
    cols = ", ".join(keys)
    self._cursor.execute(
        f"SELECT {cols} FROM Divisions{conditions}",
        args,
    )
    return [dict(zip(keys, row)) for row in self._cursor.fetchall()]

  def list_teams(self, conditions: str = "", *args):
    """List teams matching conditions."""
    if conditions:
      conditions = " WHERE " + conditions
    keys = [
        "season_id",
        "division_id",
        "conference_id",
        "team_id",
        "name",
        "stats",
    ]
    cols = ", ".join(keys)
    self._cursor.execute(
        f"SELECT {cols} FROM Teams{conditions}",
        args,
    )
    return [dict(zip(keys, row)) for row in self._cursor.fetchall()]

  def list_players(self, conditions: str = "", *args):
    if conditions:
      conditions = " WHERE " + conditions
    keys = ["player_id", "name", "info"]
    cols = ", ".join(keys)
    self._cursor.execute(f"SELECT {cols} FROM Players{conditions}", args)
    return [dict(zip(keys, row)) for row in self._cursor.fetchall()]

  def list_games(self, conditions: str = "", *args):
    """Load games from DB."""
    if conditions:
      conditions = " WHERE " + conditions
    keys = [
        "season_id",
        "division_id",
        "conference_id",
        "game_id",
        "homeId",
        "awayId",
        "start_time",
        "rink",
        "info",
        "stats",
    ]

    cols = ",".join(keys)
    self._cursor.execute(f"SELECT {cols} FROM Games AS g{conditions};", args)
    result = []
    for row in self._cursor.fetchall():
      row = dict(zip(keys, row))
      if row["info"]:
        row["info"] = json.loads(row["info"])
      if row["stats"]:
        row["stats"] = json.loads(row["stats"])
      result.append(row)
    return result

  # Add methods

  def add_season(self, season_id: int, name: str):
    """Inserts season."""

    existing = self.get_season(season_id)
    if existing:
      if existing["name"] == "Current":
        # Overwrite Current.
        pass
      elif existing["name"] == name:
        return existing
      else:
        print(
            "Overwriting season %s with %s"
            % (existing, (season_id, name))
        )

    query = "INSERT OR REPLACE INTO SEASONS (season_id, name) VALUES (?, ?)"

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

    existing = self.get_division(division_id, conference_id)
    if existing:
      if existing["name"] == name:
        return existing
      else:
        print("Overwriting div %s with %s" % (existing["name"], name))

    query = (
        "INSERT OR REPLACE INTO Divisions (division_id, conference_id, name)"
        " VALUES (?, ?, ?)"
    )

    self._cursor.execute(query, (division_id, conference_id, name))
    self._conn.commit()
    return self._cursor.lastrowid

  def add_team(
      self,
      season_id: int,
      division_id: int,
      conference_id: int,
      team_id: int,
      name: str,
      stats: dict[str, Any],
  ):
    """Inserts team."""

    # Always override team stats.
    query = (
        "INSERT OR REPLACE INTO Teams (season_id, division_id,"
        " conference_id, team_id, name, stats) VALUES (?, ?, ?, ?, ?, ?)"
    )

    self._cursor.execute(
        query,
        (
            season_id,
            division_id,
            conference_id,
            team_id,
            name,
            json.dumps(stats),
        ),
    )
    self._conn.commit()
    return self._cursor.lastrowid

  def add_player(self, player_id: int, name: str, info: dict[str, Any]):
    """Inserts player."""

    existing = self.get_player(player_id)
    if existing:
      if existing["name"] == name:
        return existing
      else:
        print("Overwriting player %s with %s" % (existing["name"], name))

    query = (
        "INSERT OR REPLACE INTO Players (player_id, name, info) VALUES (?,"
        " ?, ?)"
    )

    self._cursor.execute(query, (player_id, name, json.dumps(info)))
    self._conn.commit()
    return self._cursor.lastrowid

  def add_game(
      self,
      season_id: int,
      division_id: int,
      conference_id: int,
      game_id: int,
      home_id: int,
      away_id: int,
      rink: str,
      start_time: datetime.datetime,
      info: dict[str, Any],
  ):
    """Inserts game."""

    existing = self.get_game(game_id)
    if existing:
      if existing["info"] == info:
        return existing
      print("Overwriting %s with %s" % (existing, info))
      return existing

    query = """
        INSERT OR REPLACE INTO Games (
            season_id,
            division_id,
            conference_id,
            game_id,
            start_time,
            rink,
            homeId,
            awayId,
            info
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")

    self._cursor.execute(
        query,
        (
            season_id,
            division_id,
            conference_id,
            game_id,
            start_time_str,
            rink,
            home_id,
            away_id,
            json.dumps(info),
        ),
    )
    self._conn.commit()
    return self._cursor.lastrowid

  def add_game_stats(self, game_id: int, stats: dict[str, Any]):
    """Inserts game stats."""

    # Always override game stats.
    query = "UPDATE OR REPLACE Games SET stats = ? WHERE game_id = ?"

    self._cursor.execute(query, (json.dumps(stats), game_id))
    self._conn.commit()
    return self._cursor.lastrowid

  # Helpers
  def ex(self, s: str):
    self._cursor.execute(s)
    if "select" in s.lower():
      return self._cursor.fetchall()
    self._conn.commit()

  def list_games_info(self, conditions: str = "", *args):
    """Load games from DB."""
    if conditions:
      conditions = " WHERE " + conditions
    self._cursor.execute(
        f"""SELECT
          (SELECT name FROM Seasons WHERE season_id = g.season_id) as season,
          (SELECT name FROM Divisions WHERE division_id = g.division_id AND conference_id = g.conference_id) as division,
          (SELECT name FROM Teams WHERE team_id = g.homeId) as home,
          (SELECT name FROM Teams WHERE team_id = g.awayId) as away,
          g.game_id,
          g.start_time,
          g.rink,
          g.info,
          g.stats
        FROM Games AS g{conditions};""",
        args,
    )
    result = []
    keys = [
        "season",
        "division",
        "home",
        "away",
        "game_id",
        "start_time",
        "rink",
        "info",
        "stats",
    ]
    for row in self._cursor.fetchall():
      row = dict(zip(keys, row))
      if row["info"]:
        row["info"] = json.loads(row["info"])
      if row["stats"]:
        row["stats"] = json.loads(row["stats"])
      result.append(row)
    return result


if __name__ == "__main__":
  db = Database()
  db.create_tables()
  print("Database and tables created successfully!")
