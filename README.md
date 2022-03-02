# Sharks Ice TimeToScore REST API

I designed this REST API to serve Solar4America Sharks Ice league stats. Data is cached locally when it is parsed from https://stats.sharksice.timetoscore.com/display-stats.php?league=1&season=0. This is very fragile.

## Endpoints
TODO: Add documentation for endpoints

### /divisions

### /divisions/{div\_id}/conference/{conf\_id}

### /games/{game\_id}

### teams/{team\_id}


References:
* uWSGI + Nginx setup by following instructions at https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uswgi-and-nginx-on-ubuntu-18-04
* Let's Encrypt for SSL Cert: https://www.digitalocean.com/community/tutorials/how-to-secure-nginx-with-let-s-encrypt-on-ubuntu-18-04