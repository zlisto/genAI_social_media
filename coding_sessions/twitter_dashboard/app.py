import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import os
from dotenv import load_dotenv
import openai
import re
import json
import random
import plotly.graph_objects as go
import plotly.express as px

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Tweet Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-weight: 600;
        padding: 0.75rem;
        border-radius: 0.5rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1565a0;
    }
    .report-container {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-top: 1rem;
    }
    /* Text wrapping for dataframe */
    .stDataFrame {
        font-size: 0.9rem;
    }
    .stDataFrame td {
        white-space: normal !important;
        word-wrap: break-word !important;
        max-width: 400px;
    }
    .stDataFrame th[data-testid*="text"] {
        min-width: 300px;
    }
    /* Sidebar navigation styling */
    .stRadio > div {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .stRadio label {
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
        border: 2px solid #4a5568;
        background-color: #2d3748 !important;
        color: #e2e8f0 !important;
        transition: all 0.3s ease;
        cursor: pointer;
        font-weight: 500;
    }
    .stRadio label:hover {
        background-color: #4a5568 !important;
        border-color: #1f77b4;
        color: #ffffff !important;
    }
    .stRadio input:checked + label {
        background-color: #1f77b4 !important;
        color: #ffffff !important;
        border-color: #1f77b4;
        font-weight: 600;
    }
    .stRadio input:not(:checked) + label {
        color: #e2e8f0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'personality_done' not in st.session_state:
    st.session_state.personality_done = False
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = "Overview"
if 'generated_tweet' not in st.session_state:
    st.session_state.generated_tweet = None

def load_data(uploaded_file):
    """Load and process CSV file"""
    try:
        df = pd.read_csv(uploaded_file)
        
        # Validate required columns
        required_cols = ['text', 'view_count', 'created_at', 'favorite_count']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"Missing required columns: {', '.join(missing_cols)}")
            return None
        
        # Convert created_at to datetime if it's not already
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        
        # Ensure numeric columns are numeric
        df['favorite_count'] = pd.to_numeric(df['favorite_count'], errors='coerce')
        df['view_count'] = pd.to_numeric(df['view_count'], errors='coerce')
        
        # Calculate engagement (favorite_count / view_count)
        df['engagement'] = df['favorite_count'] / df['view_count'].replace(0, 1)  # Avoid division by zero
        df['engagement'] = df['engagement'].fillna(0)  # Fill NaN with 0
        
        # Sort by engagement descending
        df = df.sort_values('engagement', ascending=False).reset_index(drop=True)
        
        return df
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

def create_engagement_plot(df):
    """Create scatter plot showing engagement over time"""
    # Prepare data for plotting
    plot_df = df.copy()
    plot_df['created_at_str'] = plot_df['created_at'].dt.strftime('%Y-%m-%d')
    
    chart = alt.Chart(plot_df).mark_circle(size=100, opacity=0.6).encode(
        x=alt.X('created_at:T', title='Date Posted', axis=alt.Axis(format='%Y-%m-%d')),
        y=alt.Y('engagement:Q', title='Engagement Rate (Favorites/Views)', scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip('text:N', title='Tweet Text'),
            alt.Tooltip('created_at:T', title='Date', format='%Y-%m-%d %H:%M'),
            alt.Tooltip('engagement:Q', title='Engagement', format='.4f'),
            alt.Tooltip('favorite_count:Q', title='Favorites'),
            alt.Tooltip('view_count:Q', title='Views')
        ],
        color=alt.Color('engagement:Q', 
                       scale=alt.Scale(scheme='greens'),
                       legend=alt.Legend(title='Engagement'))
    ).properties(
        width=800,
        height=500,
        title='Engagement Rate Over Time'
    ).interactive()
    
    return chart

def create_scatter_plot(df):
    """Create scatter plot with Altair showing favorite count over time"""
    # Prepare data for plotting
    plot_df = df.copy()
    plot_df['created_at_str'] = plot_df['created_at'].dt.strftime('%Y-%m-%d')
    
    chart = alt.Chart(plot_df).mark_circle(size=100, opacity=0.6).encode(
        x=alt.X('created_at:T', title='Date Posted', axis=alt.Axis(format='%Y-%m-%d')),
        y=alt.Y('favorite_count:Q', title='Favorite Count', scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip('text:N', title='Tweet Text'),
            alt.Tooltip('created_at:T', title='Date', format='%Y-%m-%d %H:%M'),
            alt.Tooltip('favorite_count:Q', title='Favorites'),
            alt.Tooltip('view_count:Q', title='Views'),
            alt.Tooltip('engagement:Q', title='Engagement', format='.4f')
        ],
        color=alt.Color('favorite_count:Q', 
                       scale=alt.Scale(scheme='blues'),
                       legend=alt.Legend(title='Favorites'))
    ).properties(
        width=800,
        height=500,
        title='Favorite Count Over Time'
    ).interactive()
    
    return chart

def analyze_vibe(df):
    """Send tweets to OpenAI for analysis"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_api_key:
        st.error("OPENAI_API_KEY not found in .env file. Please add it.")
        return None
    
    try:
        # Prepare data for analysis - take top tweets and sample
        analysis_df = df[['text', 'favorite_count']].copy()
        
        # Create a summary of the data
        sample_size = min(50, len(analysis_df))
        sample_df = analysis_df.head(sample_size)
        
        # Format tweets for analysis
        tweets_data = []
        for idx, row in sample_df.iterrows():
            tweets_data.append({
                'text': row['text'],
                'favorite_count': int(row['favorite_count'])
            })
        
        # Create prompt
        prompt = f"""Analyze the following Twitter/X posts and their engagement metrics. Provide a professional marketing report.

Here are the tweets with their favorite counts:
{str(tweets_data)}

CRITICAL: Return ONLY valid HTML code in this EXACT format. Do NOT use markdown. Do NOT wrap in code blocks. Start directly with the HTML tags below:

<div style="font-family: Arial, sans-serif;">
<h1 style="color: #1f77b4; border-bottom: 3px solid #1f77b4; padding-bottom: 10px;">Marketing Analysis Report</h1>

<h2 style="color: #333; margin-top: 30px; margin-bottom: 15px;">1. Persona Analysis</h2>
<p style="line-height: 1.8; color: #555; margin-bottom: 20px;">[Describe the persona/voice of this account based on writing style, topics, and tone]</p>

<h2 style="color: #333; margin-top: 30px; margin-bottom: 15px;">2. Writing Style</h2>
<p style="line-height: 1.8; color: #555; margin-bottom: 20px;">[Analyze writing patterns, language use, and communication style]</p>

<h2 style="color: #333; margin-top: 30px; margin-bottom: 15px;">3. Engagement Insights</h2>
<p style="line-height: 1.8; color: #555; margin-bottom: 20px;">[Identify what types of content, topics, or styles correlate with higher engagement]</p>
</div>

Return ONLY the HTML code above with your analysis filled in. Use <p>, <strong>, <em>, <ul>, <li> tags as needed. No markdown, no code blocks, just pure HTML."""

        # Call OpenAI API
        client = openai.OpenAI(api_key=openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional social media marketing analyst. You MUST return ONLY valid HTML code. Never use markdown syntax. Never wrap your response in code blocks. Always return pure HTML that can be directly rendered in a browser."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"Error analyzing tweets: {str(e)}")
        return None

def analyze_personality(df):
    """Analyze personality traits from tweets and return scores for radar plot"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_api_key:
        st.error("OPENAI_API_KEY not found in .env file. Please add it.")
        return None
    
    try:
        # Prepare data for analysis - take sample of tweets
        analysis_df = df[['text']].copy()
        sample_size = min(50, len(analysis_df))
        sample_df = analysis_df.head(sample_size)
        
        # Combine all tweet texts
        all_tweets = "\n".join([f"- {text}" for text in sample_df['text'].tolist()])
        
        # Create prompt for personality analysis
        prompt = f"""Analyze the personality traits of the author based on these Twitter/X posts. Rate each trait on a scale of 0-100.

Tweets:
{all_tweets}

Return ONLY a valid JSON object with these exact personality traits and their scores (0-100):
{{
    "Extraversion": <score>,
    "Openness": <score>,
    "Conscientiousness": <score>,
    "Agreeableness": <score>,
    "Neuroticism": <score>,
    "Assertiveness": <score>,
    "Creativity": <score>,
    "Analytical": <score>
}}

Also include a "summary" field with a brief Myers-Briggs style personality description (2-3 sentences).

Return ONLY the JSON, no markdown, no code blocks, no explanations."""

        # Call OpenAI API
        client = openai.OpenAI(api_key=openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a personality psychologist. You MUST return ONLY valid JSON. Never use markdown. Never wrap your response in code blocks. Always return pure JSON that can be directly parsed."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        st.error(f"Error analyzing personality: {str(e)}")
        return None

def create_radar_plot(personality_data):
    """Create a radar plot from personality scores"""
    # Extract scores (exclude summary)
    traits = []
    scores = []
    
    for key, value in personality_data.items():
        if key != "summary" and isinstance(value, (int, float)):
            traits.append(key)
            scores.append(value)
    
    # Create radar chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=scores,
        theta=traits,
        fill='toself',
        name='Personality Profile',
        line_color='#1f77b4',
        fillcolor='rgba(31, 119, 180, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10)
            ),
            angularaxis=dict(
                tickfont=dict(size=11)
            )
        ),
        showlegend=True,
        title={
            'text': 'Personality Profile Analysis',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#1f77b4'}
        },
        height=600,
        font=dict(family="Arial, sans-serif")
    )
    
    return fig

def generate_tweet(df):
    """Generate a tweet using AI based on user's writing style and engagement patterns"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_api_key:
        st.error("OPENAI_API_KEY not found in .env file. Please add it.")
        return None
    
    try:
        # Prepare data for analysis - take sample of tweets
        analysis_df = df[['text', 'favorite_count']].copy()
        sample_size = min(30, len(analysis_df))
        sample_df = analysis_df.head(sample_size)
        
        # Get current date and time
        current_datetime = datetime.now()
        current_date_str = current_datetime.strftime('%Y-%m-%d')
        current_time_str = current_datetime.strftime('%H:%M')
        day_of_week = current_datetime.strftime('%A')
        
        # Combine tweet texts with their engagement scores
        tweets_with_engagement = []
        for idx, row in sample_df.iterrows():
            tweets_with_engagement.append({
                'text': row['text'],
                'favorite_count': int(row['favorite_count'])
            })
        
        # Create prompt
        prompt = f"""Based on the following Twitter/X posts and their engagement metrics (favorite_count), generate a new tweet that this person would likely post.

Current date and time: {current_date_str} {current_time_str} ({day_of_week})

Previous tweets with engagement:
{json.dumps(tweets_with_engagement, indent=2)}

Generate a tweet that:
1. Matches this person's writing style, tone, and voice
2. Would be engaging based on what has worked well for them (high favorite_count tweets)
3. Is appropriate for the current date/time context
4. Is authentic to their persona

CRITICAL: Return ONLY the tweet text itself. Nothing else. No explanations, no quotes, no markdown formatting, no code blocks, no prefixes, no suffixes. Just the raw tweet text and nothing more."""

        # Call OpenAI API
        client = openai.OpenAI(api_key=openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a social media content generator. You MUST return ONLY the tweet text. No markdown, no quotes, no explanations, no code blocks, no prefixes, no suffixes. Just the raw tweet text and absolutely nothing else."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=280
        )
        
        tweet_text = response.choices[0].message.content.strip()
        # Remove quotes, markdown code blocks, and any other formatting
        tweet_text = tweet_text.strip('"').strip("'").strip()
        tweet_text = re.sub(r'^```.*?\n', '', tweet_text, flags=re.DOTALL)
        tweet_text = re.sub(r'\n```.*?$', '', tweet_text, flags=re.DOTALL)
        tweet_text = tweet_text.strip()
        
        return tweet_text
        
    except Exception as e:
        st.error(f"Error generating tweet: {str(e)}")
        return None

# Main app
st.markdown('<p class="main-header">📊 Tweet Analytics Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload your tweet data and gain insights into your engagement patterns</p>', unsafe_allow_html=True)

# Sidebar for navigation and file upload
with st.sidebar:
    st.header("📁 Data Upload")
    uploaded_file = st.file_uploader(
        "Upload CSV file",
        type=['csv'],
        help="CSV file must contain columns: text, view_count, created_at, favorite_count"
    )
    
    if uploaded_file is not None:
        if st.session_state.df is None or st.button("Reload Data"):
            st.session_state.df = load_data(uploaded_file)
            st.session_state.analysis_done = False
            st.session_state.personality_done = False
    
    st.divider()
    
    # Navigation tabs
    if st.session_state.df is not None:
        st.header("📑 Navigation")
        tabs = [
            "📊 Overview",
            "📈 Engagement Chart",
            "🔍 Marketing Analysis",
            "🧠 Personality Profile",
            "✍️ Generate Tweet"
        ]
        
        selected = st.radio(
            "Select a section:",
            tabs,
            index=tabs.index(st.session_state.selected_tab) if st.session_state.selected_tab in tabs else 0,
            label_visibility="collapsed"
        )
        st.session_state.selected_tab = selected

# Main content area
if st.session_state.df is not None:
    df = st.session_state.df.copy()
    
    # Ensure engagement column exists (for backward compatibility)
    if 'engagement' not in df.columns:
        df['engagement'] = df['favorite_count'] / df['view_count'].replace(0, 1)
        df['engagement'] = df['engagement'].fillna(0)
        # Re-sort by engagement
        df = df.sort_values('engagement', ascending=False).reset_index(drop=True)
        st.session_state.df = df
    
    selected_tab = st.session_state.selected_tab
    
    # Overview Tab
    if selected_tab == "📊 Overview":
        st.header("📊 Overview Dashboard")
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Tweets", len(df))
        with col2:
            st.metric("Total Favorites", f"{int(df['favorite_count'].sum()):,}")
        with col3:
            st.metric("Avg Favorites", f"{int(df['favorite_count'].mean()):,.0f}")
        with col4:
            st.metric("Max Favorites", f"{int(df['favorite_count'].max()):,}")
        
        st.divider()
        
        # Display table with sort options
        st.header("📋 Tweets Table")
        
        # Sort options
        col_sort1, col_sort2 = st.columns([3, 1])
        
        with col_sort1:
            sort_column = st.selectbox(
                "Sort by:",
                options=['engagement', 'favorite_count', 'view_count', 'created_at'],
                format_func=lambda x: {
                    'engagement': 'Engagement Rate',
                    'favorite_count': 'Favorite Count',
                    'view_count': 'View Count',
                    'created_at': 'Date Posted'
                }.get(x, x),
                index=0,
                key="sort_column"
            )
        
        with col_sort2:
            sort_order = st.radio(
                "Order:",
                options=['Descending', 'Ascending'],
                index=0,
                horizontal=True,
                key="sort_order"
            )
        
        # Sort the dataframe
        ascending = (sort_order == 'Ascending')
        df_sorted = df.sort_values(sort_column, ascending=ascending).reset_index(drop=True)
        
        st.dataframe(
            df_sorted[['text', 'created_at', 'engagement', 'favorite_count', 'view_count']],
            use_container_width=True,
            height=600,
            hide_index=True,
            column_config={
                "text": st.column_config.TextColumn(
                    "Tweet Text",
                    width="large",
                    help="Full tweet text content"
                ),
                "created_at": st.column_config.DatetimeColumn(
                    "Date Posted",
                    format="YYYY-MM-DD HH:mm"
                ),
                "engagement": st.column_config.NumberColumn(
                    "Engagement",
                    format="%.4f",
                    help="Favorites / Views"
                ),
                "favorite_count": st.column_config.NumberColumn(
                    "Favorites",
                    format="%d"
                ),
                "view_count": st.column_config.NumberColumn(
                    "Views",
                    format="%d"
                )
            }
        )
    
    # Engagement Chart Tab
    elif selected_tab == "📈 Engagement Chart":
        st.header("📈 Engagement Analysis")
        
        # Engagement Rate Plot (first)
        st.subheader("Engagement Rate Over Time")
        st.markdown("Engagement rate = Favorites / Views. Higher values indicate more effective content.")
        engagement_chart = create_engagement_plot(df)
        st.altair_chart(engagement_chart, use_container_width=True)
        
        st.divider()
        
        # Favorite Count Plot (second)
        st.subheader("Favorite Count Over Time")
        st.markdown("Total number of favorites received over time.")
        favorite_chart = create_scatter_plot(df)
        st.altair_chart(favorite_chart, use_container_width=True)
    
    # Marketing Analysis Tab
    elif selected_tab == "🔍 Marketing Analysis":
        st.header("🔍 AI-Powered Marketing Analysis")
        st.markdown("Get professional insights about your persona, writing style, and engagement patterns.")
        
        if st.button("Analyze My Vibe", type="primary", use_container_width=True):
            with st.spinner("Analyzing your tweets with AI... This may take a moment."):
                analysis_result = analyze_vibe(df)
                
                if analysis_result:
                    st.session_state.analysis_done = True
                    st.session_state.analysis_result = analysis_result
        
        if st.session_state.analysis_done and 'analysis_result' in st.session_state:
            # Clean HTML - remove markdown code blocks if present
            html_content = st.session_state.analysis_result.strip()
            
            # Remove markdown code blocks (```html or ```)
            html_content = re.sub(r'```html?\s*\n?', '', html_content)
            html_content = re.sub(r'```\s*\n?', '', html_content)
            html_content = html_content.strip()
            
            # If the content doesn't start with HTML tags, OpenAI might have returned markdown
            # Try to convert common markdown to HTML
            if not html_content.startswith('<'):
                # Convert markdown headers to HTML
                html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
                html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
                html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
                html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
                html_content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_content)
                # Convert line breaks to paragraphs
                paragraphs = [p.strip() for p in html_content.split('\n\n') if p.strip()]
                html_content = '\n'.join([f'<p>{p}</p>' if not p.startswith('<') else p for p in paragraphs])
            
            # Wrap in styled container
            styled_html = f"""
            <div style="background-color: #ffffff; padding: 2rem; border-radius: 0.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 1rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333;">
                {html_content}
            </div>
            """
            
            st.markdown(styled_html, unsafe_allow_html=True)
        else:
            st.info("👆 Click the button above to generate your marketing analysis report.")
    
    # Personality Profile Tab
    elif selected_tab == "🧠 Personality Profile":
        st.header("🧠 Personality Profile Analysis")
        st.markdown("Discover your personality traits based on your writing style and content.")
        
        if st.button("Analyze My Personality", type="primary", use_container_width=True):
            with st.spinner("Analyzing personality traits from your tweets... This may take a moment."):
                personality_result = analyze_personality(df)
                
                if personality_result:
                    st.session_state.personality_done = True
                    st.session_state.personality_data = personality_result
        
        if st.session_state.personality_done and 'personality_data' in st.session_state:
            personality_data = st.session_state.personality_data
            
            # Display radar plot
            radar_fig = create_radar_plot(personality_data)
            st.plotly_chart(radar_fig, use_container_width=True)
            
            # Display summary if available
            if 'summary' in personality_data:
                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 1.5rem; border-radius: 0.5rem; margin-top: 1rem; border-left: 4px solid #1f77b4;">
                    <h3 style="color: #1f77b4; margin-top: 0;">Personality Summary</h3>
                    <p style="line-height: 1.8; color: #333; margin-bottom: 0;">{personality_data['summary']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Display trait scores in a nice format
            st.markdown("### Trait Scores")
            trait_cols = st.columns(4)
            trait_items = [(k, v) for k, v in personality_data.items() if k != 'summary' and isinstance(v, (int, float))]
            
            for idx, (trait, score) in enumerate(trait_items):
                with trait_cols[idx % 4]:
                    st.metric(trait, f"{int(score)}/100")
        else:
            st.info("👆 Click the button above to generate your personality profile.")
    
    # Generate Tweet Tab
    elif selected_tab == "✍️ Generate Tweet":
        st.header("✍️ Generate Tweet")
        st.markdown("Generate a new tweet based on your writing style and engagement patterns.")
        
        # 1. The Button
        if st.button("Generate Tweet", type="primary", use_container_width=True):
            with st.spinner("Generating your tweet..."):
                tweet_text = generate_tweet(df)
                if tweet_text:
                    st.session_state.generated_tweet = tweet_text
        
        # 2. The Display (Native Streamlit Components)
        if st.session_state.get("generated_tweet"):
            st.markdown("### Preview")
            
            # Center the content with columns to constrain width
            col_left, col_center, col_right = st.columns([1, 2, 1])
            
            with col_center:
                # Create a container with a border (Looks like a card)
                with st.container(border=True):
                    # Create two columns: Small one for avatar, Big one for text
                    col1, col2 = st.columns([1, 6])
                    
                    with col1:
                        # Use a standard Twitter egg avatar
                        st.image("https://abs.twimg.com/sticky/default_profile_images/default_profile_400x400.png", width=50)
                    
                    with col2:
                        # The Header
                        st.markdown("**AI Agent** *@yourhandle* · Just now")
                        
                        # The Tweet Text
                        # We use st.write to handle newlines automatically
                        st.write(st.session_state.generated_tweet)
                        
                        # Fake Interaction Icons (Just text for vibes)
                        st.caption("💬 24  🔁 12  ❤️ 158  📊 12K")
            
        else:
            st.info("👆 Click the button above to generate a tweet.")
else:
    st.info("👈 Please upload a CSV file using the sidebar to get started.")
    st.markdown("""
    ### Expected CSV Format:
    Your CSV file should contain the following columns:
    - **text**: The tweet text content
    - **view_count**: Number of views
    - **created_at**: Date/time of the tweet (will be parsed automatically)
    - **favorite_count**: Number of favorites/likes
    
    ### Example:
    ```csv
    text,view_count,created_at,favorite_count
    "This is a great tweet!",1500,2024-01-15 10:30:00,45
    "Another amazing post",2000,2024-01-16 14:20:00,78
    ```
    """)
