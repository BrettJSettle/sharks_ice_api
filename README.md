# Sharks Ice TimeToScore REST API

I designed this REST API to serve Solar4America Sharks Ice league stats. Data is scraped from https://stats.sharksice.timetoscore.com/display-stats.php?league=1&season=0 and downstream links, and cached locally with a maximum age of a few days. This is very fragile so please reach out to me before relying on it.


## Endpoints

Base URL: http://bsettle.com/sharks_ice/api

Notes:
* The `seasonId` field can be an ID from the `/seasons` endpoint, or the string `"current"` for the current season.
* Add `reload=true` to the end of any endpoint to bypass cached data and force a new scrape.
* Internal errors will return `{error: <message>}` to the caller.

### `/`

Returns information about the list of endpoints below.

### `/seasons`

#### Response
```js
{
  seasons: {
    [season name: str]: [seasonId: int]
  }
}
```

### `/seasons/<seasonId>/divisions`
Scrapes divisions and team stats from the https://stats.sharksice.timetoscore.com/display-stats.php.

#### Reponse
```js
{
divisions: [{
  id: string,
  conferenceId: string,
  seasonId: string,
  name: string,
  teams: [{
    id: string,
    name: string,
    gamesPlayed: string,
    wins: string,
    losses: string,
    ties: string,
    overtimeLosses: string,
    streak: string,
    tieBreaker: string
  }]
}]
}
```

### `/seasons/<seasonId>/divisions/<divisionId>/conference/<conferenceId>`
Scrapes division player stats from https://stats.sharksice.timetoscore.com/display-league-stats

Notes:
* `/seasons/<seasonId>/divisions/<divisionId>` will use the default value of `conferenceId=0`

#### Response
```js
{
  players: [{
    team: string,
    name: string,
    number: string,
    gamesPlayed: int,
    goals: int,
    assists: int,
    points: int,
    ppg: double,
    hatTricks: int,
    penaltyMinutes: int
  }],
  goalies: [{
    team: string,
    name: string,
    gamesPlayed: int,
    shots: int,
    goalsAgainst: int,
    goalsAgainstAverage: double,
    savePercentage: double,
    shutouts: int
  ]}
}
```

### `/seasons/{seasonId}/teams/{teamId}`
Scrapes team games stats from https://stats.sharksice.timetoscore.com/display-schedule

#### Response
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
    homeGoals: int,
    awayGoals: int,
  }]
}
```

### `/games/{gameId}`
Scrapes game scoresheet stats from https://stats.sharksice.timetoscore.com/oss-scoresheet

#### Reponse
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
  away: string,
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
    offIce: string,
    start: string,
    end: string,
    onIce: string,
  }],
  homeShootouts: [{
    name: string,
    number: string,
    result: string,
  }],
  awayGoals: ...,
  awayPlayers: ...,
  awayScoring: ...,
  awayPenalties: ...,
  awayShootouts: ...  
}
```

## References:
* uWSGI + Nginx setup by following instructions at https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uswgi-and-nginx-on-ubuntu-18-04
* Let's Encrypt for SSL Cert: https://www.digitalocean.com/community/tutorials/how-to-secure-nginx-with-let-s-encrypt-on-ubuntu-18-04
