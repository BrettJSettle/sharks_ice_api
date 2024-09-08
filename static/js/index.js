
// // Grid Options: Contains all of the Data Grid configurations
// const gridOptions = {
//   // Row Data: The data to be displayed.
//   rowData: [
//     {make: 'Tesla', model: 'Model Y', price: 64950, electric: true},
//     {make: 'Ford', model: 'F-Series', price: 33850, electric: false},
//     {make: 'Toyota', model: 'Corolla', price: 29600, electric: false},
//   ],
//   // Column Definitions: Defines the columns to be displayed.
//   columnDefs:
//       [{field: 'make'}, {field: 'model'}, {field: 'price'}, {field:
//       'electric'}]
// };

// // Your Javascript code to create the Data Grid
// const myGridElement = document.querySelector('#myGrid');
// agGrid.createGrid(myGridElement, gridOptions);

let gridApi;

const gridOptions = {
  getRowId: function(params) {
    // the ID can be any string, as long as it's unique within your dataset
    const link = `<a
              href="https://stats.sharksice.timetoscore.com/oss-scoresheet?game_id=${
        params.data.game_id}&mode=display" target="_blank">${
        params.data.game_id}</a>`;
    return link;
  },
  columnDefs: [
    // this row shows the row index, doesn't use any data from the row
    {
      headerName: 'ID',
      maxWidth: 100,
      // it is important to have node.id here, so that when the id changes
      // (which happens when the row is loaded) then the cell is refreshed.
      valueGetter: 'node.id',
      cellRenderer: (params) => {
        if (params.value !== undefined) {
          return params.value;
        } else {
          return '<img src="https://www.ag-grid.com/example-assets/loading.gif">';
        }
      },
    },
    {
      field: 'rink',
      minWidth: 150,
      filter: true,
    },
    {
      field: 'level',
      minWidth: 150,
      filter: true,
    },
    {
      field: 'date',
      minWidth: 150,
      filter: true,
    },
    {
      field: 'time',
      minWidth: 150,
      filter: true,
    },
    {
      field: 'home',
      valueGetter: params => {
        const link = `<a href="/team?team_id=${params.data.team_id}</a>`;
        return link;
      },
      minWidth: 150,
    },
    {
      field: 'away',
      valueGetter: params => {
        const link = `<a href="/team?team_id=${params.data.team_id}</a>`;
        return link;
      },
      minWidth: 150,
    },
    // {field: 'stats', minWidth: 150},
  ],
  defaultColDef: {
    flex: 1,
    minWidth: 100,
    sortable: false,
  },
  rowBuffer: 0,
  pagination: true,
  // paginationAutoPageSize: true,
  paginationPageSizeSelector: [20, 50, 100, 300],
  paginationPageSize: 100,

  // rowModelType: 'infinite',
  // how big each page in our page cache will be, default is 100
  // cacheBlockSize: 100,
  // how many extra blank rows to display to the user at the end of the dataset,
  // which sets the vertical scroll and then allows the grid to request viewing
  // more rows of data. default is 1, ie show 1 row.
  // cacheOverflowSize: 1,
  // how many server side requests to send at a time. if user is scrolling lots,
  // then the requests are throttled down
  // maxConcurrentDatasourceRequests: 1,
  // how many rows to initially show in the grid. having 1 shows a blank row, so
  // it looks like the grid is loading from the users perspective (as we have a
  // spinner in the first col)
  // infiniteInitialRowCount: 1000,
  // how many pages to store in cache. default is undefined, which allows an
  // infinite sized cache, pages are never purged. this should be set for large
  // data to stop your browser from getting full of data
  // maxBlocksInCache: 10,
  // Prevent loading until scrolling stops.
  // blockLoadDebounceMillis: 1000,

  // debug: true,
};

// setup the grid after the page has finished loading
document.addEventListener('DOMContentLoaded', function() {
  const gridDiv = document.querySelector('#myGrid');
  gridApi = agGrid.createGrid(gridDiv, gridOptions);

  fetch('http://localhost:5000/api/games?' + new URLSearchParams({
                                               'season_id': 64,
                                             }).toString())
      .then((response) => response.json())
      .then((data) => gridApi.setGridOption('rowData', data.games));

  // const dataSource = {
  //   rowCount: undefined,  // behave as infinite scroll
  //   getRows: (params) => {
  //     console.log(params.startRow + ' to ' + params.endRow);
  //     fetch('http://localhost:5000/api/games?' + new URLSearchParams({
  //                                                  'startRow':
  //                                                  params.startRow, 'endRow':
  //                                                  params.endRow, 'seasonId':
  //                                                  64,
  //                                                }).toString())
  //         .then((response) => response.json())
  //         .then((data) => {
  //           let games = data.games;
  //           // take a slice of the total rows
  //           const rowsThisPage = games.slice(params.startRow, params.endRow);
  //           // if on or after the last page, work out the last row.
  //           let lastRow = -1;
  //           if (games.length <= params.endRow) {
  //             lastRow = games.length;
  //           }
  //           params.successCallback(rowsThisPage, lastRow);
  //         });
  //   },
  // };

  // gridApi.setGridOption('datasource', dataSource);
});