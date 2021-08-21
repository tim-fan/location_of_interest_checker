# Location of Interest Checker

Script to compare COVID locations of interest to Google location history.

## Usage

### Export Google location history

1) Go to https://takeout.google.com/
2) Under 'CREATE A NEW EXPORT`, deselect all, then select 'Location History', then 'Next Step'
3) Follow instructions to download, then unzip exported data. This tool uses the file 'Location History.json'

### Install

To install this script into a virtualenv:



### Run 

```bash
location_of_interest_checker ../Location\ History.json /tmp/distance_to_locations.csv
```