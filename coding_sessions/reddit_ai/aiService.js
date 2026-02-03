import OpenAI from 'openai';

const CONFIG = {
  apiKey: process.env.REACT_APP_OPENAI_API_KEY,
  model: process.env.REACT_APP_MODEL || 'gpt-5-nano'
};

// Initialize OpenAI client
let openaiClient = null;

const getOpenAIClient = () => {
  if (!CONFIG.apiKey || CONFIG.apiKey === 'your_api_key_here') {
    throw new Error('OpenAI API key not configured. Please set REACT_APP_OPENAI_API_KEY in .env file');
  }

  if (!openaiClient) {
    openaiClient = new OpenAI({
      apiKey: CONFIG.apiKey,
      dangerouslyAllowBrowser: true // Required for browser usage
    });
  }

  return openaiClient;
};

export const callOpenAI = async (prompt, isJson = false) => {
  try {
    const client = getOpenAIClient();
    
    const params = {
      model: CONFIG.model,
      messages: [
        {
          role: 'user',
          content: prompt
        }
      ],
      max_completion_tokens: 10000
    };

    // Trigger JSON Mode if requested
    if (isJson) {
      params.response_format = { type: "json_object" };
    }

    const completion = await client.chat.completions.create(params);
    
    console.log('=== OPENAI RESPONSE ===');
    console.log('Full completion:', JSON.stringify(completion, null, 2));
    console.log('Choices:', completion.choices);
    console.log('First choice:', completion.choices?.[0]);
    console.log('Message:', completion.choices?.[0]?.message);
    
    const content = completion.choices[0]?.message?.content;
    
    console.log('Content:', content);
    console.log('Content type:', typeof content);
    console.log('Content length:', content?.length);

    if (!content) {
      console.error('=== NO CONTENT ERROR ===');
      console.error('Full completion object:', completion);
      console.error('Choices array:', completion.choices);
      console.error('First choice details:', completion.choices?.[0]);
      throw new Error('No content in OpenAI response. Check console for details.');
    }

    return content.trim();
  } catch (error) {
    console.error('OpenAI API call failed:', error);
    throw error;
  }
};
