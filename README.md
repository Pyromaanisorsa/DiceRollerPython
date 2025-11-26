# DiceRollerPython
Companion App / TCP-server to connect GoDice D20 bluetooth dice to [DiceRollers Unity project](https://github.com/Pyromaanisorsa/DiceRollers/tree/main).
Used to send GoDice roll values to AWS, which will be used to send the roll values to Unity via internet.

![Screenshot of the app](DiceRollerPython.png)

How-to-use
1. Start the app via terminal
2. Connect your GoDice with Connect button
3. Type your username/playerID you typed in the game
4. Toggle ready state with ready button when you wanna send roll results to AWS
5. Roll the GoDice and it should send the roll value to AWS on stable roll
6. AWS returns HTTP response from Lambda function
