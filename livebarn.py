import datetime

LIVEBARN_RINKS = {
    'San Jose South': 547,
    'San Jose North': 546,
    'San Jose East': 548,
    'San Jose Center': 549,
}
LIVEBARN_URL = 'https://livebarn.com/en/videov/?begindate={date}&sid={sid}'


def time_in_seconds(game_time: str):
    parts = list(map(float, game_time.split(':', 1)))
    minutes, seconds = 0, 0
    if len(parts) == 1:
        seconds = parts[0]
    else:
        minutes = parts[0]
        seconds = parts[1]
    return int(minutes * 60 + seconds)


def _estimate_time(
        game_start_time: datetime.datetime,
        period: int,
        time_remaining: str,
        period_minutes: int = 22):
    seconds_remaining = time_in_seconds(time_remaining)
    seconds_remaining = datetime.timedelta(seconds=seconds_remaining)
    estimate = game_start_time + datetime.timedelta(minutes=5)  # warmups
    period_minutes = datetime.timedelta(
        minutes=period_minutes)  # estimate periods at 22m
    estimate += period_minutes * (period - 1)
    # Time is time remaining in period
    estimate += (period_minutes - seconds_remaining)
    return estimate

def add_livebarn_links(start, data):
    rink = data['rink']
    for goal in data['goals']:
        estimated_time = _estimate_time(start, goal['period'], goal['time'])
        goal['livebarn'] = get_livebarn_url(estimated_time, rink)

    for penalty in data['penalties']:
        estimated_time = _estimate_time(
            start, penalty['period'], penalty['off_ice_time'])
        penalty['livebarn'] = get_livebarn_url(estimated_time, rink)


def get_livebarn_url(date: datetime.datetime, rink: str):
    sid = LIVEBARN_RINKS[rink]
    if date.minute % 30 != 0:
        date -= datetime.timedelta(minutes=date.minute % 30)
    date = datetime.datetime.strftime(date, '%Y-%m-%dT%H:%M')
    return LIVEBARN_URL.format(date=date, sid=sid)
