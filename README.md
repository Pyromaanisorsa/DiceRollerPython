# DiceRollerPython
Companion App / TCP-server to connect GoDice D20 bluetooth dice to [DiceRollers Unity project](https://github.com/Pyromaanisorsa/DiceRollers/tree/main).
Created with PyQt and Qt Designer. Used to send GoDice roll values to AWS, which will be used to send the roll values to Unity via internet.

![Screenshot of the app](DiceRollerPython.png)
Figure: Screenshot of the app.

If you wanna modify the app I recommend running it in venv.
To modify the UI either:
1. Modify the DiceWindow.ui with Qt Designer and convert the .ui file to .py file with terminal command.
```
pyuic6 DiceWindow.ui -o DiceWindow.py
```
2. Modify the DiceWindow.py file directly.

How-to-use:
1. Start the app via terminal
2. Connect your GoDice with Connect button
3. Type your username/playerID you typed in the game
4. Toggle ready state with ready button when you wanna send roll results to AWS
5. Roll the GoDice and it should send the roll value to AWS on stable roll
6. AWS returns HTTP response from Lambda function (no rollRequest currently, result sent successfully, error)

