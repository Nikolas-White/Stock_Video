import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this to a secure secret in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Limit uploads (e.g., 500MB)

# Allowed video file extensions
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

db = SQLAlchemy(app)

# Ensure the uploads folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Database model for videos
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    tags = db.Column(db.String(250), nullable=True)
    filename = db.Column(db.String(250), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Video {self.title}>'

# Create the database tables before the first request
@app.before_first_request
def create_tables():
    db.create_all()

# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Homepage: lists videos and handles search queries
@app.route('/')
def index():
    search_query = request.args.get('q', '')
    if search_query:
        # Case-insensitive search in title or tags
        videos = Video.query.filter(
            (Video.title.ilike(f'%{search_query}%')) |
            (Video.tags.ilike(f'%{search_query}%'))
        ).all()
    else:
        videos = Video.query.order_by(Video.upload_date.desc()).all()
    return render_template('index.html', videos=videos, search_query=search_query)

# Upload page: displays a form and processes uploads
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        title = request.form.get('title')
        tags = request.form.get('tags')
        file = request.files.get('video')

        if not title or not file:
            flash('A title and a video file are required.')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Create a unique filename to avoid collisions
            original_filename = file.filename
            unique_filename = datetime.utcnow().strftime('%Y%m%d%H%M%S%f_') + original_filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)

            # Save video metadata to the database
            new_video = Video(title=title, tags=tags, filename=unique_filename)
            db.session.add(new_video)
            db.session.commit()

            flash('Video uploaded successfully!')
            return redirect(url_for('index'))
        else:
            flash('Invalid file type. Please upload a valid video file.')
            return redirect(request.url)
    return render_template('upload.html')

# Download route: serves the video file as an attachment
@app.route('/download/<int:video_id>')
def download(video_id):
    video = Video.query.get_or_404(video_id)
    # The download_name parameter is used in newer Flask versions (>=2.2);
    # if you have an older version, you may need to use attachment_filename=video.title.
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               video.filename,
                               as_attachment=True,
                               download_name=video.title)

if __name__ == '__main__':
    app.run(debug=True)
