import os
os.system('clear')
print('WELCOME to Musicana!')
print('Please give a star on github')
print(' Installing all the packages so you get no error')
path = '/data/data/com.termux/files/home/MUSICANA/Lyrica'
check = os.path.exists(path)
if check ==  False:
   os.system('git clone https://github.com/Wilooper/Lyrica.git')
else:
 def none():
   return 0

os.system('pip install Flask flask-cors Flask-Caching ytmusicapi pytubefix requests')

print('Installing done You have no need to run this script next time!')
print('Made with Love by Wilooper')
print('Thanks!')
