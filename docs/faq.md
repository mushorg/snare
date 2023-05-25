# Frequently Asked Questions

### White Pages

Once the cloning is done and you try to serve the pages via snare, you might get all the white pages and nothing else. 

In this scenario, there are two things to make sure of:

1. You are using the latest code from the Snare repository.
    - For extra measure, make sure to compare the versions in the requirement.txt on the remote main branch(https://github.com/mushorg/snare/tree/main) and the code you have.

2. Make sure you have the tanner running properly.
    - If you are using the public tanner instance i.e. tanner.mushmush.org:8090, make sure it is responding.
    - If any Tanner instance is running properly, once you visit the Tanner URL in your browser you should see `Tanner Server` on the page.
        - In most of the scenarios when Tanner isn't working properly snare might serve white pages instead of throwing any error.

