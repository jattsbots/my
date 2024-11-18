import os
import ffmpeg
import tempfile
import shutil
import logging
from telegram import Update, Bot, File, ParseMode, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from uuid import uuid4

# --- Configuration ---
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN" # Replace with your bot's token
MAX_FILES = 10 # Maximum number of videos to merge at once

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- User Sessions ---
user_sessions = {}

# --- Helper Functions ---

def start(update: Update, context: CallbackContext):
  """Starts a new merge session for the user."""
  user_id = update.effective_chat.id
  user_sessions[user_id] = {"temp_dir": tempfile.mkdtemp(), "files": []}
  update.message.reply_text(f"Send me up to {MAX_FILES} videos to merge. Type /merge when done.")
  log_action(f"User {user_id} started a new merge session.")

def add_video(update: Update, context: CallbackContext):
  """Adds a video to the user's current merge session."""
  user_id = update.effective_chat.id
  if user_id not in user_sessions:
    start(update, context) # Start a session if one doesn't exist
    return

  if len(user_sessions[user_id]["files"]) >= MAX_FILES:
    update.message.reply_text(f"Maximum number of files ({MAX_FILES}) reached. Type /merge to process.")
    return

  file = update.message.video
  file_id = file.file_id
  file_path = os.path.join(user_sessions[user_id]["temp_dir"], f"{file_id}.mp4")

  try:
    new_file = context.bot.get_file(file_id)
    new_file.download(file_path) # Download in chunks
    user_sessions[user_id]["files"].append(file_path)
    update.message.reply_text(f"Added video with file ID: {file_id}")
    log_action(f"User {user_id} added video {file_id}")
  except Exception as e:
    update.message.reply_text(f"Error downloading video: {e}")
    log_action(f"Error downloading video for user {user_id}: {e}")

def merge_videos(user_id, context):
  """Merges the videos in the user's session using ffmpeg."""
  files = user_sessions[user_id]["files"]
  temp_dir = user_sessions[user_id]["temp_dir"]
  if not files:
    return "No videos to merge."

  context.bot.send_chat_action(chat_id=user_id, action=ChatAction.UPLOAD_VIDEO)
  output_file = os.path.join(temp_dir, "merged_video.mp4")

  try:
    inputs = [ffmpeg.input(f) for f in files]
    concat_filter = ffmpeg.filter.vconcat(*inputs) # Vertical concatenation
    output = ffmpeg.output(concat_filter, output_file)
    output.run()
    return output_file
  except ffmpeg.Error as e:
    return f"FFmpeg error: {e}"
  except Exception as e:
    return f"An error occurred: {e}"

def merge(update: Update, context: CallbackContext):
  """Handles the /merge command to process videos."""
  user_id = update.effective_chat.id
  if user_id not in user_sessions:
    update.message.reply_text("No active session. Start a new one with /start.")
    return

  merged_file_path = merge_videos(user_id, context)

  if isinstance(merged_file_path, str) and merged_file_path.startswith(("FFmpeg error:", "An error occurred:")):
    update.message.reply_text(merged_file_path) # Report error
    log_action(f"User {user_id} merge failed: {merged_file_path}")
  elif merged_file_path:
    try:
      with open(merged_file_path, 'rb') as f:
        context.bot.send_video(user_id, f, supports_streaming=True)
    except Exception as e:
      update.message.reply_text(f"Error sending merged video: {e}")
      log_action(f"Error sending merged video for user {user_id}: {e}")
    finally:
      shutil.rmtree(user_sessions[user_id]["temp_dir"])
      del user_sessions[user_id]
      log_action(f"User {user_id} finished merging. File sent.")
  else:
    update.message.reply_text("No videos added to merge.")
    shutil.rmtree(user_sessions[user_id]["temp_dir"])
    del user_sessions[user_id]


def cancel(update: Update, context: CallbackContext):
  """Cancels the user's current merge session."""
  user_id = update.effective_chat.id
  if user_id in user_sessions:
    shutil.rmtree(user_sessions[user_id]["temp_dir"])
    del user_sessions[user_id]
  update.message.reply_text("Session canceled.")
  log_action(f"User {user_id} canceled session.")


def log_action(message):
  """Logs an action (for debugging and monitoring). Replace with your logging method."""
  logger.info(message)


def main():
  """Starts the bot."""
  bot = Bot(token=BOT_TOKEN)
  updater = Updater(BOT_TOKEN, use_context=True)
  dp = updater.dispatcher

  dp.add_handler(CommandHandler("start", start))
  dp.add_handler(MessageHandler(Filters.video, add_video))
  dp.add_handler(CommandHandler("merge", merge))
  dp.add_handler(CommandHandler("cancel", cancel))

  updater.start_polling()
  updater.idle()

if __name__ == "__main__":
  main()
