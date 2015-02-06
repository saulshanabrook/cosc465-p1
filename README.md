

## Mac

Install
```bash
brew install xquartz
brew install socat
brew cask install xquartz
```

Run
```bash
open -a XQuartz
socat TCP-LISTEN:6000,reuseaddr,fork UNIX-CLIENT:\"$DISPLAY\"
# in another window
fig up
```

## Non Mac
???
Maybe
```
socat TCP-LISTEN:6000,reuseaddr,fork UNIX-CLIENT:\"$DISPLAY\"
fig up
```
