import os
import ffmpeg
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Initialize the bot using your Telegram bot's token
bot = Bot(token="YOUR_TELEGRAM_BOT_TOKEN")

# Define the directory where videos will be stored and merged
UPLOAD_FOLDER = 'videos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def merge_videos(input_files, output_file):
  """Merges multiple video files using ffmpeg-python."""
  try:
    # Create a new ffmpeg.input object for each input file
    inputs = [ffmpeg.input(f) for f in input_files]
    # Concatenate the inputs
    concat_filter = ffmpeg.filter.vconcat(*inputs)
    # Set the output file
    output = ffmpeg.output(concat_filter, output_file)
    # Run the ffmpeg command
    output.run()
    return output_file
  except ffmpeg.Error as e:
    print(f"An error occurred: {e}")
    return None

def handle_video_merge(update: Update, context: Context):
  """Handles the /merge command.
  Downloads all videos sent to the bot and merges them into a single video.
  Then sends the merged video back to the user.
  Args:
    update: The Telegram update object.
    context: The Telegram context object.
  """
  user_id = update.effective_chat.id
  # Get the list of video files sent by the user
  videos = context.bot.get_updates(offset=-1, limit=100, timeout=10)[-1].message.video

  # Create a list of video file paths
  input_files = []
  for video in videos:
    file_id = video.file_id
    file = context.bot.get_file(file_id)
    file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.mp4")
    file.download(file_path)
    input_files.append(file_path)

  # Merge the videos
  output_file = os.path.join(UPLOAD_FOLDER, "merged_video.mp4")
  merged_file_path = merge_videos(input_files, output_file)

  # Send the merged video to the user
  if merged_file_path:
    bot.send_video(user_id, open(merged_file_path, 'rb'), supports_streaming=True)
  else:
    bot.send_message(user_id, "An error occurred while merging the videos. Please try again.")

def main():
  # Create the Updater object
  updater = Updater(bot.token, use_context=True)

  # Add the message handler for the /merge command
  updater.dispatcher.add_handler(CommandHandler("merge", handle_video_merge))

  # Start the Updater object
  updater.start_polling()

  # Run the bot until the user presses Ctrl-C
  updater.idle()

if __name__ == "__main__":
  main()
