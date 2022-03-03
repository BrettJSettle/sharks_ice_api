# Sharks Ice TimeToScore REST API

I designed this REST API to serve Solar4America Sharks Ice league stats. Data is cached locally when it is parsed from https://stats.sharksice.timetoscore.com/display-stats.php?league=1&season=0. This is very fragile.

## Endpoints

Base URL: http://bsettle.com/sharks_ice/api/

### /

Returns the list of resources.

### /divisions
Scrapes divisions and team stats from the [main stats page](https://stats.sharksice.timetoscore.com/display-stats.php).

Reponse
```js
{
divisions: [{
  id: string,
  conference_id: string,
  season_id: string,
  name: string,
  teams: [{
    id: string,
    name: string,
    GP: string,
    W: string,
    L: string,
    T: string,
    OTL: string,
    Streak: string,
    Tie Breaker: string
  }]
}]
}```

### /divisions/{div\_id}/conference/{conf\_id}
Response
```js
{
  players: [{
    team: string,
    name: string,
    number: string,
    games_played: int,
    goals: int,
    assists: int,
    points: int,
    ppg: double,
    hat_tricks: int,
    penalty_minutes: int
  }],
  goalies: [{
    team: string,
    name: string,
    games_played: int,
    shots: int,
    goals_against: int,
    goals_against_average: double,
    save_percentage: double,
    shutouts: int
  ]}
}
```

### /games/{game\_id}

Reponse
```js
{
  date: string,
  time: string,
  rink: string,
  periodLength: string,
  league: string,
  level: string,
  referee1: string,
  referee2: string,
  scorekeeper: string,
  home: string,
  visitor: string,
  homeGoals: int,
  homePlayers: [{
    name: string,
    number: string,
    position: string,
  }],
  homeScoring: [{
    period: string,
    time: string,
    number: string,
    extra: string,
    assist1: string,
    assist2: string,
  }],
  homePenalties: [{
    number: string,
    time: string,
    period: string,
    minutes: string,
    infraction: string,
    off_ice: string,
    start: string,
    end: string,
    on_ice: string,
  }],
  homeShootouts: [{
    name: string,
    number: string,
    result: string,
  }],
  visitorGoals: ...,
  visitorPlayers: ...,
  visitorScoring: ...,
  visitorPenalties: ...,
  visitorShootouts: ...  
}
```

### teams/{team\_id}

Response
```js
{
  calendar: string,
  games: [{
    id: string,
    date: string,
    time: string,
    rink: string,
    league: string,
    level: string,
    home: string,
    away: string,
    type: string,
    home_goals: int,
    away_goals: int,
  }]
}
```

References:
* uWSGI + Nginx setup by following instructions at https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uswgi-and-nginx-on-ubuntu-18-04
* Let's Encrypt for SSL Cert: https://www.digitalocean.com/community/tutorials/how-to-secure-nginx-with-let-s-encrypt-on-ubuntu-18-04
