import React, { useState, useEffect, useRef } from 'react';
import { FileUp, Shield, Book, RefreshCw, Settings, Info, Save, BarChart3, ChevronDown, Download, Loader2, Search, Plus, Edit, Trash2, X, Check, Key } from 'lucide-react';
import axios from 'axios';

// API base URL - using absolute path for development, relative for production
const API_URL = import.meta.env.DEV ? 'http://localhost:5002/api' : '/api';

// Default PIN code for dictionary modifications
const DEFAULT_PIN = '1324';

// Interfaces for type safety
interface Statistics {
  totalCorrections: number;
  protectedTermsCount: number;
  correctionTermsCount: number;
}

interface ProcessResult {
  original_filename: string;
  corrected_filename: string;
  replacements: Record<string, number>;
  download_url: string;
}

interface ProcessResponse {
  status: string;
  results: ProcessResult[];
  total_replacements: Record<string, number>;
  statistics: Statistics;
}

function App() {
  const [files, setFiles] = useState<File[]>([]);
  const [protectedTerms, setProtectedTerms] = useState<string>('');
  const [correctionTerms, setCorrectionTerms] = useState<string>('');
  const [statistics, setStatistics] = useState<Statistics>({
    totalCorrections: 0,
    protectedTermsCount: 0,
    correctionTermsCount: 0
  });

  // Additional state variables
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [results, setResults] = useState<ProcessResult[]>([]);
  const [dictionaryLoading, setDictionaryLoading] = useState<boolean>(false);
  const [dictionarySaving, setDictionarySaving] = useState<boolean>(false);
  const [processingProgress, setProcessingProgress] = useState<number>(0);

  // State for term management
  const [showTermModal, setShowTermModal] = useState(false);
  const [termModalMode, setTermModalMode] = useState<'add' | 'edit'>('add');
  const [termModalType, setTermModalType] = useState<'correction' | 'protection'>('correction');
  const [termModalTerm, setTermModalTerm] = useState('');
  const [termModalValue, setTermModalValue] = useState('');
  const [termModalPin, setTermModalPin] = useState(DEFAULT_PIN);
  const [termSearchQuery, setTermSearchQuery] = useState('');
  const [termSearchResults, setTermSearchResults] = useState<{correction: Record<string, string>, protection: Record<string, string>}>({correction: {}, protection: {}});
  const [termSearchLoading, setTermSearchLoading] = useState(false);

  // State for info and settings modals
  const [showInfoModal, setShowInfoModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [animationEnabled, setAnimationEnabled] = useState(true);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  // Load dictionaries when component mounts
  useEffect(() => {
    loadDictionaries();
  }, []);

  // Apply theme when it changes
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  // Toggle theme function
  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
    // Show notification if enabled
    if (notificationsEnabled) {
      const message = theme === 'light' ? 'Dark mode activated' : 'Light mode activated';
      showNotification(message);
    }
  };

  // Show notification function
  const showNotification = (message: string) => {
    const notification = document.getElementById('notification');
    if (notification) {
      const messageElement = notification.querySelector('.message');
      if (messageElement) {
        messageElement.textContent = message;
      }
      notification.classList.remove('hidden');
      notification.classList.add('animate-slide-in');

      setTimeout(() => {
        notification.classList.remove('animate-slide-in');
        notification.classList.add('animate-fade-out');
        setTimeout(() => {
          notification.classList.add('hidden');
          notification.classList.remove('animate-fade-out');
        }, 500);
      }, 3000);
    }
  };

  // Function to load dictionaries from the API
  const loadDictionaries = async () => {
    setDictionaryLoading(true);
    setError('');
    try {
      // Load protection dictionary
      const protectionResponse = await axios.get(`${API_URL}/dictionaries/protection`);
      const protectionDict = protectionResponse.data;

      // Load correction dictionary
      const correctionResponse = await axios.get(`${API_URL}/dictionaries/correction`);
      const correctionDict = correctionResponse.data;

      // Convert dictionaries to string format for textareas
      setProtectedTerms(Object.keys(protectionDict).join('\n'));
      setCorrectionsFromDict(correctionDict);

      // Update statistics
      setStatistics(prev => ({
        ...prev,
        protectedTermsCount: Object.keys(protectionDict).length,
        correctionTermsCount: Object.keys(correctionDict).length
      }));
    } catch (err) {
      console.error('Error loading dictionaries:', err);
      setError('Failed to load dictionaries. Please try again.');
    } finally {
      setDictionaryLoading(false);
    }
  };

  // Helper function to convert correction dictionary to string format
  const setCorrectionsFromDict = (dict: Record<string, string>) => {
    const lines = Object.entries(dict).map(([key, value]) => {
      return value ? `${key} -> ${value}` : key;
    });
    setCorrectionTerms(lines.join('\n'));
  };

  // Helper function to parse correction terms string into dictionary
  const parseCorrectionsToDict = (text: string): Record<string, string> => {
    const dict: Record<string, string> = {};
    text.split('\n').forEach(line => {
      const trimmed = line.trim();
      if (trimmed) {
        if (trimmed.includes(' -> ')) {
          const [key, value] = trimmed.split(' -> ');
          dict[key.trim()] = value.trim();
        } else {
          dict[trimmed] = '';
        }
      }
    });
    return dict;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) {
      setError('Please select at least one SRT file to process');
      return;
    }

    setLoading(true);
    setError('');
    setResults([]);
    setProcessingProgress(0);

    try {
      // Create form data for file upload
      const formData = new FormData();
      // Process all files
      files.forEach((file, index) => {
        formData.append('files', file);
        console.log(`Adding file ${index + 1}/${files.length} to form data:`, file.name, file.size);
      });

      console.log('Sending request to:', `${API_URL}/process`);

      // Simulate progress while waiting for response
      const progressInterval = setInterval(() => {
        setProcessingProgress(prev => {
          // Slowly increase progress up to 85% while waiting for response
          if (prev < 85) {
            return prev + Math.random() * 3; // Add a random amount for more natural progress
          }
          return prev;
        });
      }, 200);

      // Send files to API for processing
      console.log('Sending request to API...');
      try {
        const response = await axios.post<any>(`${API_URL}/process`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });

        console.log('Response received:', response.data);

        // Clear progress interval and set to 100%
        clearInterval(progressInterval);

        // Check if response has the expected format
        if (!response.data || !response.data.task_id) {
          throw new Error('Invalid response format: ' + JSON.stringify(response.data));
        }

        // Start polling for task status
        const taskId = response.data.task_id;
        console.log('Task ID:', taskId);

        // Poll for task status
        let taskCompleted = false;
        let pollCount = 0;
        const maxPolls = 1800; // Maximum number of polls (1800 seconds = 30 minutes)

        while (!taskCompleted && pollCount < maxPolls) {
          await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
          pollCount++;

          console.log(`Polling task status (${pollCount}/${maxPolls})...`);
          const taskResponse = await axios.get(`${API_URL}/tasks/${taskId}`);
          console.log('Task status:', taskResponse.data);

          if (taskResponse.data.status === 'completed') {
            // Task completed successfully
            taskCompleted = true;

            // Update results with task result
            if (taskResponse.data.results && Array.isArray(taskResponse.data.results)) {
              // Multiple files result
              const newResults = taskResponse.data.results.map(result => ({
                original_filename: result.original_filename || '',
                corrected_filename: result.corrected_file || '',
                replacements: result.replacements || {},
                download_url: result.download_url || ''
              }));

              setResults(newResults);
              setStatistics(prev => ({
                ...prev,
                totalCorrections: taskResponse.data.statistics?.totalCorrections || 0
              }));
            } else {
              // Single file result (backward compatibility)
              const result = {
                original_filename: taskResponse.data.file_name,
                corrected_filename: taskResponse.data.result?.corrected_file || '',
                replacements: taskResponse.data.result?.replacements || {},
                download_url: taskResponse.data.download_url || ''
              };

              setResults([result]);
              setStatistics(prev => ({
                ...prev,
                totalCorrections: taskResponse.data.result?.total_replacements || 0
              }));
            }

            break;
          } else if (taskResponse.data.status === 'error') {
            // Task failed
            throw new Error('Task failed: ' + (taskResponse.data.error || 'Unknown error'));
          }

          // Update progress
          setProcessingProgress(taskResponse.data.progress || 0);
        }

        if (!taskCompleted) {
          throw new Error('Task timed out after ' + maxPolls + ' seconds');
        }
      } catch (error) {
        console.error('Error in API request:', error);
        throw error; // Re-throw to be caught by the outer catch block
      }

      // Set progress to 100%
      setProcessingProgress(100);

      // Scroll to results section
      setTimeout(() => {
        const resultsSection = document.querySelector('.results-section');
        if (resultsSection) {
          resultsSection.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);

    } catch (err: any) {
      console.error('Error processing files:', err);

      // Animate progress bar to show error state
      const errorAnimation = () => {
        setProcessingProgress(prev => {
          // Quickly decrease to 0
          const newProgress = prev * 0.8;
          return newProgress < 1 ? 0 : newProgress;
        });
      };

      const errorInterval = setInterval(errorAnimation, 50);

      // Ensure we reach 0% after a short delay
      setTimeout(() => {
        clearInterval(errorInterval);
        setProcessingProgress(0);
      }, 500);

      if (err.response) {
        console.error('Response data:', err.response.data);
        console.error('Response status:', err.response.status);
        setError(`Failed to process files: ${err.response.status} ${JSON.stringify(err.response.data)}`);
      } else if (err.request) {
        console.error('No response received:', err.request);
        setError('Failed to process files: No response received from server');
      } else {
        console.error('Error message:', err.message);
        setError(`Failed to process files: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDictionaries = async () => {
    setDictionarySaving(true);
    setError('');

    try {
      // Parse protected terms into dictionary
      const protectionDict: Record<string, string> = {};
      protectedTerms.split('\n').forEach(term => {
        const trimmed = term.trim();
        if (trimmed) {
          protectionDict[trimmed] = '';
        }
      });

      // Parse correction terms into dictionary
      const correctionDict = parseCorrectionsToDict(correctionTerms);

      // Save dictionaries to API
      await Promise.all([
        axios.post(`${API_URL}/dictionaries/protection`, {
          pin: DEFAULT_PIN,
          dictionary: protectionDict
        }),
        axios.post(`${API_URL}/dictionaries/correction`, {
          pin: DEFAULT_PIN,
          dictionary: correctionDict
        })
      ]);

      // Update statistics
      setStatistics(prev => ({
        ...prev,
        protectedTermsCount: Object.keys(protectionDict).length,
        correctionTermsCount: Object.keys(correctionDict).length
      }));
    } catch (err) {
      console.error('Error saving dictionaries:', err);
      setError('Failed to save dictionaries. Please try again.');
    } finally {
      setDictionarySaving(false);
    }
  };

  // Function to open the term modal for adding a new term
  const handleAddTerm = (type: 'correction' | 'protection') => {
    setTermModalMode('add');
    setTermModalType(type);
    setTermModalTerm('');
    setTermModalValue('');
    setShowTermModal(true);
  };

  // Function to open the term modal for editing an existing term
  const handleEditTerm = (type: 'correction' | 'protection', term: string, value: string = '') => {
    setTermModalMode('edit');
    setTermModalType(type);
    setTermModalTerm(term);
    setTermModalValue(value);
    setShowTermModal(true);
  };

  // Function to save a term (add or edit)
  const handleSaveTerm = async () => {
    if (!termModalTerm.trim()) {
      setError('Term cannot be empty');
      return;
    }

    try {
      setDictionarySaving(true);
      setError('');

      const action = termModalMode === 'add' ? 'add' : 'update';

      const response = await axios.post(`${API_URL}/dictionaries/update-term`, {
        pin: termModalPin,
        type: termModalType,
        term: termModalTerm.trim(),
        value: termModalValue.trim(),
        action
      });

      // Close the modal and refresh dictionaries
      setShowTermModal(false);
      await loadDictionaries();

      // Show success message
      console.log(`Term ${action}ed successfully:`, response.data);
    } catch (err: any) {
      console.error(`Error ${termModalMode}ing term:`, err);
      if (err.response && err.response.status === 403) {
        setError('Invalid PIN code. Please try again.');
      } else {
        setError(`Failed to ${termModalMode} term. Please try again.`);
      }
    } finally {
      setDictionarySaving(false);
    }
  };

  // Function to delete a term
  const handleDeleteTerm = async (type: 'correction' | 'protection', term: string) => {
    if (!confirm(`Are you sure you want to delete the term "${term}"?`)) {
      return;
    }

    try {
      setDictionarySaving(true);
      setError('');

      const response = await axios.post(`${API_URL}/dictionaries/update-term`, {
        pin: DEFAULT_PIN,
        type,
        term,
        action: 'delete'
      });

      // Refresh dictionaries
      await loadDictionaries();

      // Show success message
      console.log('Term deleted successfully:', response.data);
    } catch (err: any) {
      console.error('Error deleting term:', err);
      if (err.response && err.response.status === 403) {
        setError('Invalid PIN code. Please try again.');
      } else {
        setError('Failed to delete term. Please try again.');
      }
    } finally {
      setDictionarySaving(false);
    }
  };

  // Function to search for terms
  const handleSearchTerms = async () => {
    if (!termSearchQuery.trim()) {
      setTermSearchResults({correction: {}, protection: {}});
      return;
    }

    try {
      setTermSearchLoading(true);
      setError('');

      const response = await axios.get(`${API_URL}/dictionaries/search`, {
        params: {
          q: termSearchQuery.trim(),
          type: 'all'
        }
      });

      setTermSearchResults(response.data.results);
    } catch (err) {
      console.error('Error searching terms:', err);
      setError('Failed to search terms. Please try again.');
    } finally {
      setTermSearchLoading(false);
    }
  };

  // Function to download a processed file
  const handleDownload = (url: string) => {
    // Fix double API prefix issue
    if (url.startsWith('/api/')) {
      window.location.href = `${API_URL.replace('/api', '')}${url}`;
    } else {
      window.location.href = `${API_URL}${url}`;
    }
  };

  // Function to download multiple files as a zip
  const handleDownloadAll = async () => {
    if (results.length === 0) return;

    try {
      // Get all filenames from results
      const filenames = results.map(result => {
        // Extract filename from download_url
        const url = result.download_url;
        return url.split('/').pop();
      }).filter(Boolean);

      if (filenames.length === 0) {
        setError('No files to download');
        return;
      }

      // Request zip file with all files
      const response = await axios.post(
        `${API_URL}/download-multiple`,
        { filenames },
        { responseType: 'blob' }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `corrected_files.zip`);
      document.body.appendChild(link);
      link.click();

      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
    } catch (err) {
      console.error('Error downloading files:', err);
      setError('Failed to download files. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 text-gray-900 dark:text-gray-100 transition-colors duration-300">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm fixed w-full z-10 transition-colors duration-300">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <RefreshCw className="w-6 h-6 text-blue-600" />
            <span className="text-xl font-mono font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600">
              LUMON SRT
            </span>
          </div>
          <nav className="flex items-center space-x-4">
            <button
              onClick={() => setShowInfoModal(true)}
              className="text-gray-600 hover:text-blue-600 transition-colors p-2 rounded-full hover:bg-blue-50"
              aria-label="Information"
            >
              <Info className="w-5 h-5" />
            </button>
            <button
              onClick={() => setShowSettingsModal(true)}
              className="text-gray-600 hover:text-blue-600 transition-colors p-2 rounded-full hover:bg-blue-50 relative group"
              aria-label="Settings"
            >
              <Settings className={`w-5 h-5 ${animationEnabled ? 'group-hover:animate-spin-slow' : ''}`} />
              <span className="absolute -bottom-1 -right-1 w-2 h-2 bg-blue-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"></span>
            </button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 text-center bg-gradient-to-b from-blue-50 to-gray-50 dark:from-blue-900/20 dark:to-gray-800 transition-colors duration-300">
        <div className="container mx-auto max-w-4xl">
          <h1 className="text-4xl md:text-5xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600">
            Professional SRT Correction
          </h1>
          <p className="text-xl text-gray-600 mb-12">
            Enhance your subtitles with our advanced correction system.
            Powered by Lumon's cutting-edge technology.
          </p>
          <div className="flex justify-center">
            <button onClick={() => document.getElementById('main-content')?.scrollIntoView({ behavior: 'smooth' })}
                    className="animate-bounce text-gray-400 hover:text-gray-600 transition-colors">
              <ChevronDown className="w-8 h-8" />
            </button>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <main id="main-content" className="container mx-auto px-4 py-16">
        <div className="grid md:grid-cols-2 gap-8">
          {/* Left Column */}
          <div className="space-y-8">
            {/* File Upload Section */}
            <section className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 transition-all hover:shadow-xl">
              <h2 className="text-xl font-mono mb-6 flex items-center text-gray-800 dark:text-gray-200">
                <FileUp className="w-5 h-5 mr-2 text-blue-600" />
                File Upload
              </h2>
              <div className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center hover:border-blue-400 transition-all">
                <input
                  type="file"
                  multiple
                  accept=".srt"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer block"
                >
                  <div className="mb-4">
                    <FileUp className="w-12 h-12 mx-auto text-gray-400" />
                  </div>
                  <p className="text-gray-600 dark:text-gray-300">Drop SRT files here or click to upload</p>
                  <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">Multiple files supported</p>
                </label>
              </div>
              {files.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-sm font-semibold mb-2 text-gray-700">Selected Files:</h3>
                  <ul className="space-y-2">
                    {files.map((file, index) => (
                      <li key={index} className="text-sm text-gray-600">{file.name}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>

            {/* Statistics Section */}
            <section className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 transition-all hover:shadow-xl">
              <h2 className="text-xl font-mono mb-6 flex items-center text-gray-800">
                <BarChart3 className="w-5 h-5 mr-2 text-yellow-500" />
                Statistics
              </h2>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-50 rounded-xl p-4 transition-all hover:bg-gray-100">
                  <p className="text-sm text-gray-600">Total Corrections</p>
                  <p className="text-2xl font-mono text-yellow-500">{statistics.totalCorrections}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 transition-all hover:bg-gray-100">
                  <p className="text-sm text-gray-600">Protected Terms</p>
                  <p className="text-2xl font-mono text-green-500">{statistics.protectedTermsCount}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 transition-all hover:bg-gray-100">
                  <p className="text-sm text-gray-600">Correction Terms</p>
                  <p className="text-2xl font-mono text-purple-500">{statistics.correctionTermsCount}</p>
                </div>
              </div>
            </section>
          </div>

          {/* Right Column - Dictionaries */}
          <section className="space-y-6">
            {/* Protected Terms */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 transition-all hover:shadow-xl">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-mono flex items-center text-gray-800">
                  <Shield className="w-5 h-5 mr-2 text-green-500" />
                  Protected Terms
                </h2>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleAddTerm('protection')}
                    className="flex items-center space-x-1 text-sm text-blue-500 hover:text-blue-600 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add Term</span>
                  </button>
                  <button
                    onClick={handleSaveDictionaries}
                    disabled={dictionarySaving || dictionaryLoading}
                    className="flex items-center space-x-1 text-sm text-green-500 hover:text-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {dictionarySaving ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Saving...</span>
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4" />
                        <span>Save Changes</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
              <textarea
                value={protectedTerms}
                onChange={(e) => setProtectedTerms(e.target.value)}
                disabled={dictionaryLoading}
                className="w-full h-32 bg-gray-50 border border-gray-200 rounded-xl p-3 text-sm focus:border-green-400 focus:ring-1 focus:ring-green-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                placeholder="Enter protected terms (one per line)"
              />
              <p className="mt-2 text-xs text-gray-500">Format: One term per line. Example: "dall-e"</p>
            </div>

            {/* Correction Terms */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 transition-all hover:shadow-xl">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-mono flex items-center text-gray-800">
                  <Book className="w-5 h-5 mr-2 text-purple-500" />
                  Correction Terms
                </h2>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleAddTerm('correction')}
                    className="flex items-center space-x-1 text-sm text-blue-500 hover:text-blue-600 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add Term</span>
                  </button>
                  <button
                    onClick={handleSaveDictionaries}
                    disabled={dictionarySaving || dictionaryLoading}
                    className="flex items-center space-x-1 text-sm text-purple-500 hover:text-purple-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {dictionarySaving ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Saving...</span>
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4" />
                        <span>Save Changes</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
              <textarea
                value={correctionTerms}
                onChange={(e) => setCorrectionTerms(e.target.value)}
                disabled={dictionaryLoading}
                className="w-full h-32 bg-gray-50 border border-gray-200 rounded-xl p-3 text-sm focus:border-purple-400 focus:ring-1 focus:ring-purple-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                placeholder="Enter correction terms (one per line)"
              />
              <p className="mt-2 text-xs text-gray-500">Format: "wrong term" or "wrong term {'->'} correct term"</p>
            </div>
          </section>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-600">
            {error}
          </div>
        )}

        {/* Results Section */}
        {results.length > 0 && (
          <section className="mt-8 bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 transition-all hover:shadow-xl results-section">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-mono flex items-center text-gray-800">
                <RefreshCw className="w-5 h-5 mr-2 text-blue-600" />
                Processing Results
              </h2>
              <button
                onClick={handleDownloadAll}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md"
              >
                <Download className="w-5 h-5" />
                <span>Download All Files</span>
              </button>
            </div>
            <div className="space-y-4">
              {results.map((result, index) => (
                <div key={index} className="p-4 bg-gray-50 rounded-xl">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="font-semibold text-gray-800">{result.original_filename}</h3>
                    <button
                      onClick={() => handleDownload(result.download_url)}
                      className="flex items-center space-x-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
                    >
                      <Download className="w-3 h-3" />
                      <span>Download</span>
                    </button>
                  </div>
                  {Object.keys(result.replacements).length > 0 ? (
                    <div className="text-sm text-gray-600">
                      <p className="mb-1">Replacements:</p>
                      <ul className="list-disc pl-5 space-y-1">
                        {Object.entries(result.replacements).map(([key, count], i) => (
                          <li key={i}>{key}: {count} times</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-600">No replacements needed</p>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Submit Button and Progress Bar */}
        <div className="mt-12 text-center">
          <button
            onClick={handleSubmit}
            disabled={loading || files.length === 0}
            className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-3 rounded-xl font-mono shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-1 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center space-x-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Processing...</span>
              </>
            ) : (
              <span>Process Files</span>
            )}
          </button>

          {/* Progress Bar */}
          {loading && (
            <div className="mt-6 w-full max-w-md mx-auto">
              <div className="bg-gray-200 rounded-full h-3 mb-1 overflow-hidden shadow-inner">
                <div
                  className="bg-gradient-to-r from-blue-600 to-purple-600 h-3 rounded-full transition-all duration-300 ease-in-out relative"
                  style={{ width: `${processingProgress}%` }}
                >
                  {/* Animated shine effect */}
                  <div className="absolute inset-0 w-full h-full">
                    <div className="absolute inset-0 -left-full animate-[shine_1.5s_infinite] bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
                  </div>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <p className="text-xs text-gray-500">{Math.round(processingProgress)}% Complete</p>
                {processingProgress > 0 && processingProgress < 100 && (
                  <p className="text-xs text-gray-500 animate-pulse">Processing...</p>
                )}
                {processingProgress === 100 && (
                  <p className="text-xs text-green-500">Complete!</p>
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-700 py-8 bg-white dark:bg-gray-800 transition-colors duration-300">
        <div className="container mx-auto px-4 text-center text-gray-500 text-sm">
          <p>© 2025 Lumon Industries. Please enjoy all files equally.</p>
        </div>
      </footer>

      {/* Term Management Modal */}
      {showTermModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 relative">
            <button
              onClick={() => setShowTermModal(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-xl font-semibold mb-4">
              {termModalMode === 'add' ? 'Add' : 'Edit'} {termModalType === 'correction' ? 'Correction' : 'Protection'} Term
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Term
                </label>
                <input
                  type="text"
                  value={termModalTerm}
                  onChange={(e) => setTermModalTerm(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={termModalType === 'correction' ? 'Wrong term' : 'Term to protect'}
                />
              </div>

              {termModalType === 'correction' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Correction
                  </label>
                  <input
                    type="text"
                    value={termModalValue}
                    onChange={(e) => setTermModalValue(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Correct term (leave empty to delete)"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  PIN Code
                </label>
                <div className="relative">
                  <input
                    type="password"
                    value={termModalPin}
                    onChange={(e) => setTermModalPin(e.target.value)}
                    className="w-full px-3 py-2 pl-9 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter PIN code"
                  />
                  <Key className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
                </div>
                <p className="text-xs text-gray-500 mt-1">Required to modify dictionaries</p>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowTermModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveTerm}
                  disabled={dictionarySaving}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {dictionarySaving ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      <span>Save</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Term Search Modal */}
      <div className="fixed bottom-4 right-4 z-40">
        <button
          onClick={() => document.getElementById('term-search-modal')?.classList.toggle('hidden')}
          className="bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700"
        >
          <Search className="w-5 h-5" />
        </button>
      </div>

      <div id="term-search-modal" className="fixed bottom-20 right-4 bg-white rounded-xl shadow-xl w-80 p-4 hidden z-40">
        <h4 className="text-lg font-semibold mb-3 flex items-center justify-between">
          <span>Search Terms</span>
          <button
            onClick={() => document.getElementById('term-search-modal')?.classList.add('hidden')}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </button>
        </h4>

        <div className="space-y-3">
          <div className="relative">
            <input
              type="text"
              value={termSearchQuery}
              onChange={(e) => setTermSearchQuery(e.target.value)}
              className="w-full px-3 py-2 pl-9 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Search terms..."
            />
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
          </div>

          <button
            onClick={handleSearchTerms}
            disabled={termSearchLoading}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            {termSearchLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Searching...</span>
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                <span>Search</span>
              </>
            )}
          </button>

          {(Object.keys(termSearchResults.correction).length > 0 || Object.keys(termSearchResults.protection).length > 0) && (
            <div className="mt-3 max-h-60 overflow-y-auto">
              {Object.keys(termSearchResults.correction).length > 0 && (
                <div className="mb-3">
                  <h5 className="text-sm font-semibold text-gray-700 mb-1">Correction Terms</h5>
                  <div className="space-y-2">
                    {Object.entries(termSearchResults.correction).map(([term, value]) => (
                      <div key={term} className="flex items-center justify-between bg-gray-50 p-2 rounded-md">
                        <div className="text-sm">
                          <span className="font-medium">{term}</span>
                          {value && (
                            <span className="text-gray-500"> → {value}</span>
                          )}
                        </div>
                        <div className="flex space-x-1">
                          <button
                            onClick={() => handleEditTerm('correction', term, value)}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteTerm('correction', term)}
                            className="text-red-600 hover:text-red-800"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {Object.keys(termSearchResults.protection).length > 0 && (
                <div>
                  <h5 className="text-sm font-semibold text-gray-700 mb-1">Protection Terms</h5>
                  <div className="space-y-2">
                    {Object.keys(termSearchResults.protection).map((term) => (
                      <div key={term} className="flex items-center justify-between bg-gray-50 p-2 rounded-md">
                        <div className="text-sm font-medium">{term}</div>
                        <div className="flex space-x-1">
                          <button
                            onClick={() => handleEditTerm('protection', term)}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteTerm('protection', term)}
                            className="text-red-600 hover:text-red-800"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Info Modal */}
      {showInfoModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-fade-in">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg p-6 relative animate-slide-in">
            <button
              onClick={() => setShowInfoModal(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900 mb-4">
                <Info className="w-8 h-8 text-blue-600 dark:text-blue-300" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white">About Lumon SRT</h3>
            </div>

            <div className="space-y-4 text-gray-600 dark:text-gray-300">
              <p>
                <span className="font-semibold">Lumon SRT</span> is a professional subtitle correction system designed to enhance your subtitles with advanced processing technology.
              </p>

              <div className="bg-blue-50 dark:bg-blue-900/30 p-4 rounded-lg">
                <h4 className="font-semibold text-blue-700 dark:text-blue-300 mb-2">Key Features</h4>
                <ul className="list-disc pl-5 space-y-1">
                  <li>Automatic correction of common errors</li>
                  <li>Protection of special terms and phrases</li>
                  <li>Batch processing of multiple files</li>
                  <li>Customizable correction dictionaries</li>
                  <li>PIN-protected dictionary management</li>
                </ul>
              </div>

              <p>
                Version: 1.0.0<br />
                Last Updated: April 2025
              </p>

              <div className="pt-4 border-t border-gray-200 dark:border-gray-700 mt-4">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  © 2025 Lumon Industries. All rights reserved.<br />
                  For support, contact support@lumon.com
                </p>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowInfoModal(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {showSettingsModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-fade-in">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md p-6 relative animate-slide-in">
            <button
              onClick={() => setShowSettingsModal(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-700 mb-4">
                <Settings className={`w-8 h-8 text-gray-600 dark:text-gray-300 ${animationEnabled ? 'animate-spin-slow' : ''}`} />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h3>
            </div>

            <div className="space-y-6">
              {/* Theme Toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white">Dark Mode</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Toggle between light and dark theme</p>
                </div>
                <button
                  onClick={toggleTheme}
                  className={`w-12 h-6 rounded-full flex items-center transition-colors duration-300 focus:outline-none ${theme === 'dark' ? 'bg-blue-600 justify-end' : 'bg-gray-300 justify-start'}`}
                >
                  <span className={`bg-white w-5 h-5 rounded-full shadow-md transform transition-transform duration-300 ${theme === 'dark' ? 'translate-x-0' : '-translate-x-0'}`}></span>
                </button>
              </div>

              {/* Animation Toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white">Animations</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Enable or disable UI animations</p>
                </div>
                <button
                  onClick={() => setAnimationEnabled(prev => !prev)}
                  className={`w-12 h-6 rounded-full flex items-center transition-colors duration-300 focus:outline-none ${animationEnabled ? 'bg-blue-600 justify-end' : 'bg-gray-300 justify-start'}`}
                >
                  <span className={`bg-white w-5 h-5 rounded-full shadow-md transform transition-transform duration-300 ${animationEnabled ? 'translate-x-0' : '-translate-x-0'}`}></span>
                </button>
              </div>

              {/* Notifications Toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white">Notifications</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Show system notifications</p>
                </div>
                <button
                  onClick={() => setNotificationsEnabled(prev => !prev)}
                  className={`w-12 h-6 rounded-full flex items-center transition-colors duration-300 focus:outline-none ${notificationsEnabled ? 'bg-blue-600 justify-end' : 'bg-gray-300 justify-start'}`}
                >
                  <span className={`bg-white w-5 h-5 rounded-full shadow-md transform transition-transform duration-300 ${notificationsEnabled ? 'translate-x-0' : '-translate-x-0'}`}></span>
                </button>
              </div>

              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => {
                    // Reset all settings to default
                    setTheme('light');
                    setAnimationEnabled(true);
                    setNotificationsEnabled(true);
                    if (notificationsEnabled) {
                      showNotification('Settings reset to defaults');
                    }
                    setShowSettingsModal(false);
                  }}
                  className="w-full px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors mt-2"
                >
                  Reset to Defaults
                </button>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowSettingsModal(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Save & Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Notification Toast */}
      <div id="notification" className="fixed top-4 right-4 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg hidden z-50">
        <p className="message">Notification message</p>
      </div>
    </div>
  );
}

export default App;