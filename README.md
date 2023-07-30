# restaurant-review-map

This is the code supporting the webpage [restaurant-review-map.danialdervovic.com](https://restaurant-review-map.danialdervovic.com) . The page is a map of the UK with pins pointing to any restaurant either Grace Dent or Jay Rayner have reviewed in The Guardian, with a link to the review itself. I wrote this code as an exercise in using ChatGPT as a code-writing assistant - I found it very helpful!

## Running locally

To run the code locally run the shell scripts as listed in [.github/workflows/main.yml](.github/workflows/main.yml).

## Updating data

There is a Github Actions workflow to autoupdate with new reviews each week. If there is any problematic data please create a Github Issue; or, even better, submit a PR with an edit to the SQLite db file directly.

No warranty, liability or support promised. This is a weekend project that may be useful to others.
