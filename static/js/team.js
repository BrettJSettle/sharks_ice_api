/**
 * @fileoverview Team info view
 */

document.addEventListener('DOMContentLoaded', function() {
  // JavaScript to fetch team data and populate dropdown
  // const dropdownContent = document.getElementById('teamDropdown');

  const urlParams = new URLSearchParams(window.location.search);
  fetch('/api/seasons/current/teams/' + urlParams.get('team_id'))
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(
          data => {
              console.log(data);
              // data.forEach(team => {
              //   const teamLink = document.createElement('a');
              //   teamLink.href = '#';  // You'll likely want to update this
              //   with the
              //                         // actual team page or action
              //   teamLink.textContent = team.name;  // Assuming the JSON has a
              //   'name'
              //                                      // property for the team
              //                                      name
              //   dropdownContent.appendChild(teamLink);
              // });
          })
      .catch(error => {
        console.error('There was a problem fetching the team data:', error);
        // You might want to display an error message to the user here
      });
});