# Frontend question bank

- Does the application load at all (HTTP 200, no blank screen)?
- Does the root route render without a framework error?
- Do the other critical routes render without error, blank page, or unexpected redirect?
- Does the login form render with the expected fields and a submit control?
- Does the primary authenticated view render its key sections?
- Can the user interact with the primary form without it breaking?
- Does form submission trigger the expected API request?
- Are there uncaught console errors on load or on the primary interaction?
- Are there failed network requests on load or on the primary interaction?
- Does logout return the user to a logged-out state?
