import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  User, 
  Users, 
  LogOut, 
  LogIn, 
  UserPlus,
  CheckCircle2, 
  ShieldCheck, 
  Building, 
  Lock,
  Mail,
  Server,
  Edit3,
  Save,
  RotateCcw,
  Sparkles
} from 'lucide-react';
import type { UserProfile } from '../types';

interface AuthProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: UserProfile;
  onUpdateUser: (user: UserProfile) => void;
  onLogin: (user: UserProfile) => void;
  onLogout: () => void;
}

export const DEMO_USERS: UserProfile[] = [
  {
    id: 'demo-1',
    name: 'Aditya Sharma',
    email: 'aditya.sharma@project.edu',
    role: 'Student Researcher',
    avatarText: 'AS',
    isLoggedIn: true,
    institution: 'Confidence-Aware RAG Major Project',
  },
  {
    id: 'demo-2',
    name: 'Dr. Priya Varma',
    email: 'priya.varma@legal-ai.org',
    role: 'Senior Legal Evaluator',
    avatarText: 'PV',
    isLoggedIn: true,
    institution: 'Judicial Document Intelligence Lab',
  },
  {
    id: 'demo-3',
    name: 'Vikram Singh',
    email: 'vikram.singh@gov.in',
    role: 'RTI / Revenue Officer',
    avatarText: 'VS',
    isLoggedIn: true,
    institution: 'Department of Revenue & Land Records',
  },
  {
    id: 'demo-4',
    name: 'Faculty Examiner',
    email: 'examiner@university.edu',
    role: 'External Viva Examiner',
    avatarText: 'FE',
    isLoggedIn: true,
    institution: 'B.Tech Project Evaluation Board',
  },
];

export const ROLE_PRESETS = [
  'Student Researcher',
  'Senior Legal Evaluator',
  'RTI / Revenue Officer',
  'Faculty Examiner',
  'Legal Analyst / Advocate',
  'Judicial Clerk',
];

export const AuthProfileModal: React.FC<AuthProfileModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onUpdateUser,
  onLogin,
  onLogout,
}) => {
  const [activeTab, setActiveTab] = useState<'profile' | 'switch' | 'login' | 'signup'>('profile');
  const [isEditing, setIsEditing] = useState<boolean>(false);
  
  // Profile edit fields
  const [nameInput, setNameInput] = useState<string>(currentUser.name);
  const [emailInput, setEmailInput] = useState<string>(currentUser.email);
  const [roleInput, setRoleInput] = useState<string>(currentUser.role);
  const [instInput, setInstInput] = useState<string>(currentUser.institution || '');
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string>('Profile settings updated successfully!');

  // Sign in state
  const [loginEmail, setLoginEmail] = useState<string>('');
  const [loginPassword, setLoginPassword] = useState<string>('');
  const [loginError, setLoginError] = useState<string>('');

  // Sign up state
  const [signupName, setSignupName] = useState<string>('');
  const [signupEmail, setSignupEmail] = useState<string>('');
  const [signupRole, setSignupRole] = useState<string>('Student Researcher');
  const [signupInst, setSignupInst] = useState<string>('');
  const [signupPassword, setSignupPassword] = useState<string>('');
  const [signupConfirmPassword, setSignupConfirmPassword] = useState<string>('');
  const [signupError, setSignupError] = useState<string>('');

  useEffect(() => {
    setNameInput(currentUser.name);
    setEmailInput(currentUser.email);
    setRoleInput(currentUser.role);
    setInstInput(currentUser.institution || '');
    setIsEditing(false);
  }, [currentUser, isOpen]);

  if (!isOpen) return null;

  const triggerSuccess = (msg: string) => {
    setSuccessMessage(msg);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2500);
  };

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    const initials = nameInput
      .split(' ')
      .map((w) => w[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase() || 'U';

    const updated: UserProfile = {
      ...currentUser,
      name: nameInput.trim() || 'User',
      email: emailInput.trim() || 'user@example.com',
      role: roleInput.trim() || 'Researcher',
      institution: instInput.trim() || 'Institution',
      avatarText: initials,
    };

    onUpdateUser(updated);
    setIsEditing(false);
    triggerSuccess('Profile settings updated successfully!');
  };

  const handleCancelEdit = () => {
    setNameInput(currentUser.name);
    setEmailInput(currentUser.email);
    setRoleInput(currentUser.role);
    setInstInput(currentUser.institution || '');
    setIsEditing(false);
  };

  const handleSelectDemoUser = (user: UserProfile) => {
    onLogin(user);
    setNameInput(user.name);
    setEmailInput(user.email);
    setRoleInput(user.role);
    setInstInput(user.institution || '');
    setIsEditing(false);
    setActiveTab('profile');
    triggerSuccess(`Logged in as ${user.name}`);
  };

  const handleCustomLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail.trim()) {
      setLoginError('Please enter your email address.');
      return;
    }

    const userName = loginEmail.split('@')[0].replace('.', ' ');
    const formattedName = userName
      .split(' ')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');

    const initials = formattedName
      .split(' ')
      .map((w) => w[0])
      .slice(0, 2)
      .join('')
      .toUpperCase() || 'U';

    const newUser: UserProfile = {
      id: `user-${Date.now()}`,
      name: formattedName,
      email: loginEmail.trim(),
      role: 'Legal Analyst',
      avatarText: initials,
      isLoggedIn: true,
      institution: 'DocSage Legal Intelligence',
    };

    onLogin(newUser);
    setNameInput(newUser.name);
    setEmailInput(newUser.email);
    setRoleInput(newUser.role);
    setInstInput(newUser.institution || '');
    setIsEditing(false);
    setActiveTab('profile');
    setLoginError('');
    triggerSuccess(`Welcome back, ${formattedName}!`);
  };

  const handleSignUp = (e: React.FormEvent) => {
    e.preventDefault();
    if (!signupName.trim()) {
      setSignupError('Please enter your full name.');
      return;
    }
    if (!signupEmail.trim() || !signupEmail.includes('@')) {
      setSignupError('Please enter a valid email address.');
      return;
    }
    if (signupPassword && signupPassword !== signupConfirmPassword) {
      setSignupError('Passwords do not match. Please verify.');
      return;
    }

    const initials = signupName
      .trim()
      .split(' ')
      .map((w) => w[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase() || 'U';

    const newUser: UserProfile = {
      id: `user-${Date.now()}`,
      name: signupName.trim(),
      email: signupEmail.trim(),
      role: signupRole.trim() || 'Student Researcher',
      institution: signupInst.trim() || 'Academic / Legal Institution',
      avatarText: initials,
      isLoggedIn: true,
    };

    onLogin(newUser);
    setNameInput(newUser.name);
    setEmailInput(newUser.email);
    setRoleInput(newUser.role);
    setInstInput(newUser.institution || '');
    setIsEditing(false);
    setActiveTab('profile');
    setSignupError('');
    triggerSuccess(`Account created successfully! Welcome, ${newUser.name}.`);
  };

  return (
    <div className="auth-modal-overlay" onClick={onClose}>
      <motion.div
        className="auth-modal-container"
        onClick={(e) => e.stopPropagation()}
        initial={{ scale: 0.94, opacity: 0, y: 15 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.94, opacity: 0, y: 15 }}
        transition={{ duration: 0.2 }}
      >
        {/* Modal Top Header */}
        <div className="auth-modal-header">
          <div className="auth-header-title-group">
            <div className="auth-brand-badge">
              <ShieldCheck size={18} className="text-primary" />
            </div>
            <div>
              <h3>Account & Profile</h3>
              <p>User Identity & Role Session</p>
            </div>
          </div>
          <button className="auth-modal-close-btn" onClick={onClose} title="Close Modal">
            <X size={18} />
          </button>
        </div>

        {/* User Status Banner */}
        <div className="auth-user-banner">
          <div className="auth-avatar-large">
            {currentUser.avatarText || 'AS'}
          </div>
          <div className="auth-banner-info">
            <div className="auth-banner-name-row">
              <h4>{currentUser.name}</h4>
              <span className="auth-role-pill">{currentUser.role}</span>
            </div>
            <span className="auth-banner-email">{currentUser.email}</span>
            <div className="auth-banner-institution">
              <Building size={12} />
              <span>{currentUser.institution || 'Confidence-Aware RAG Project'}</span>
            </div>
          </div>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="auth-modal-tabs">
          <button
            className={`auth-tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('profile');
              setIsEditing(false);
            }}
          >
            <User size={14} />
            <span>Profile Details</span>
          </button>
          <button
            className={`auth-tab-btn ${activeTab === 'switch' ? 'active' : ''}`}
            onClick={() => setActiveTab('switch')}
          >
            <Users size={14} />
            <span>Switch Role</span>
          </button>
          <button
            className={`auth-tab-btn ${activeTab === 'login' ? 'active' : ''}`}
            onClick={() => setActiveTab('login')}
          >
            <LogIn size={14} />
            <span>Sign In</span>
          </button>
          <button
            className={`auth-tab-btn ${activeTab === 'signup' ? 'active' : ''}`}
            onClick={() => setActiveTab('signup')}
          >
            <UserPlus size={14} />
            <span>Sign Up</span>
          </button>
        </div>

        {/* Success Alert Banner */}
        <AnimatePresence>
          {saveSuccess && (
            <motion.div
              className="auth-success-alert"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              <CheckCircle2 size={16} className="text-success" />
              <span>{successMessage}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Tab Body Content */}
        <div className="auth-modal-body">
          {/* TAB 1: Profile Details */}
          {activeTab === 'profile' && (
            <div className="auth-profile-wrapper">
              <div className="auth-callout-note">
                <Server size={18} className="text-primary flex-shrink-0" />
                <p>
                  API processing & LLM generation are connected directly to your <strong>FastAPI Backend</strong> & <strong>MongoDB Atlas</strong>.
                </p>
              </div>

              {!isEditing ? (
                /* READ-ONLY VIEW MODE */
                <div className="auth-view-grid">
                  <div className="profile-info-row">
                    <span className="info-label">Full Name</span>
                    <div className="info-value-box">
                      <User size={15} className="info-icon" />
                      <strong>{currentUser.name}</strong>
                    </div>
                  </div>

                  <div className="profile-info-row">
                    <span className="info-label">Email Address</span>
                    <div className="info-value-box">
                      <Mail size={15} className="info-icon" />
                      <span>{currentUser.email}</span>
                    </div>
                  </div>

                  <div className="profile-info-row">
                    <span className="info-label">Primary Role</span>
                    <div className="info-value-box">
                      <ShieldCheck size={15} className="info-icon" />
                      <span className="auth-role-pill-sm">{currentUser.role}</span>
                    </div>
                  </div>

                  <div className="profile-info-row">
                    <span className="info-label">Institution / Department</span>
                    <div className="info-value-box">
                      <Building size={15} className="info-icon" />
                      <span>{currentUser.institution || 'Confidence-Aware RAG Project'}</span>
                    </div>
                  </div>

                  <div className="auth-form-actions">
                    <button
                      type="button"
                      className="auth-primary-btn"
                      onClick={() => setIsEditing(true)}
                    >
                      <Edit3 size={15} />
                      <span>Edit Profile</span>
                    </button>
                    <button
                      type="button"
                      className="auth-danger-btn"
                      onClick={() => {
                        onLogout();
                        setActiveTab('login');
                      }}
                    >
                      <LogOut size={14} />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              ) : (
                /* EDIT MODE FORM */
                <form className="auth-form-grid" onSubmit={handleSaveProfile}>
                  <div className="auth-input-group">
                    <label>Full Name</label>
                    <div className="input-with-icon">
                      <User size={16} className="field-icon" />
                      <input
                        type="text"
                        value={nameInput}
                        onChange={(e) => setNameInput(e.target.value)}
                        placeholder="Enter full name"
                        required
                        autoFocus
                      />
                    </div>
                  </div>

                  <div className="auth-input-group">
                    <label>Email Address</label>
                    <div className="input-with-icon">
                      <Mail size={16} className="field-icon" />
                      <input
                        type="email"
                        value={emailInput}
                        onChange={(e) => setEmailInput(e.target.value)}
                        placeholder="name@organization.com"
                        required
                      />
                    </div>
                  </div>

                  <div className="auth-input-group">
                    <label>Primary Role</label>
                    <div className="input-with-icon">
                      <ShieldCheck size={16} className="field-icon" />
                      <input
                        type="text"
                        value={roleInput}
                        onChange={(e) => setRoleInput(e.target.value)}
                        placeholder="e.g. Student Researcher, Legal Analyst"
                        required
                      />
                    </div>
                  </div>

                  <div className="auth-input-group">
                    <label>Institution / Department</label>
                    <div className="input-with-icon">
                      <Building size={16} className="field-icon" />
                      <input
                        type="text"
                        value={instInput}
                        onChange={(e) => setInstInput(e.target.value)}
                        placeholder="e.g. Department of Computer Science"
                      />
                    </div>
                  </div>

                  <div className="auth-form-actions">
                    <button type="submit" className="auth-primary-btn">
                      <Save size={15} />
                      <span>Save Changes</span>
                    </button>
                    <button
                      type="button"
                      className="auth-secondary-btn"
                      onClick={handleCancelEdit}
                    >
                      <RotateCcw size={14} />
                      <span>Cancel</span>
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* TAB 2: Switch Demo User */}
          {activeTab === 'switch' && (
            <div className="demo-users-list">
              <p className="demo-users-intro">
                Select any predefined demo account to simulate different user personas and document access privileges:
              </p>
              <div className="demo-user-cards-grid">
                {DEMO_USERS.map((user) => {
                  const isCurrent = currentUser.name === user.name;
                  return (
                    <motion.div
                      key={user.id}
                      className={`demo-user-card ${isCurrent ? 'active' : ''}`}
                      onClick={() => handleSelectDemoUser(user)}
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                    >
                      <div className="demo-card-avatar">{user.avatarText}</div>
                      <div className="demo-card-info">
                        <div className="demo-card-top-row">
                          <strong>{user.name}</strong>
                          {isCurrent && <span className="current-badge">Active</span>}
                        </div>
                        <span className="demo-card-role">{user.role}</span>
                        <span className="demo-card-email">{user.email}</span>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 3: Sign In */}
          {activeTab === 'login' && (
            <form className="auth-form-grid" onSubmit={handleCustomLogin}>
              <p className="demo-users-intro">
                Sign in with your email or credentials for user session tracking:
              </p>

              {loginError && (
                <div className="auth-error-alert">
                  <span>{loginError}</span>
                </div>
              )}

              <div className="auth-input-group">
                <label>Email Address</label>
                <div className="input-with-icon">
                  <Mail size={16} className="field-icon" />
                  <input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="user@example.com"
                    required
                  />
                </div>
              </div>

              <div className="auth-input-group">
                <label>Password</label>
                <div className="input-with-icon">
                  <Lock size={16} className="field-icon" />
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <div className="auth-form-actions">
                <button type="submit" className="auth-primary-btn">
                  <LogIn size={14} />
                  <span>Sign In</span>
                </button>
                <button
                  type="button"
                  className="auth-link-btn"
                  onClick={() => setActiveTab('signup')}
                >
                  <span>New user? Create an account</span>
                </button>
              </div>
            </form>
          )}

          {/* TAB 4: Sign Up / Create Account */}
          {activeTab === 'signup' && (
            <form className="auth-form-grid" onSubmit={handleSignUp}>
              <p className="demo-users-intro">
                Create a new user account to customize your document analysis session:
              </p>

              {signupError && (
                <div className="auth-error-alert">
                  <span>{signupError}</span>
                </div>
              )}

              <div className="auth-input-group">
                <label>Full Name *</label>
                <div className="input-with-icon">
                  <User size={16} className="field-icon" />
                  <input
                    type="text"
                    value={signupName}
                    onChange={(e) => setSignupName(e.target.value)}
                    placeholder="e.g. Satyam Singh"
                    required
                  />
                </div>
              </div>

              <div className="auth-input-group">
                <label>Email Address *</label>
                <div className="input-with-icon">
                  <Mail size={16} className="field-icon" />
                  <input
                    type="email"
                    value={signupEmail}
                    onChange={(e) => setSignupEmail(e.target.value)}
                    placeholder="name@university.edu"
                    required
                  />
                </div>
              </div>

              <div className="auth-input-group">
                <label>Primary Role</label>
                <div className="input-with-icon">
                  <ShieldCheck size={16} className="field-icon" />
                  <select
                    className="auth-select-input"
                    value={signupRole}
                    onChange={(e) => setSignupRole(e.target.value)}
                  >
                    {ROLE_PRESETS.map((role) => (
                      <option key={role} value={role}>{role}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="auth-input-group">
                <label>Institution / Department</label>
                <div className="input-with-icon">
                  <Building size={16} className="field-icon" />
                  <input
                    type="text"
                    value={signupInst}
                    onChange={(e) => setSignupInst(e.target.value)}
                    placeholder="e.g. Computer Science & Law Lab"
                  />
                </div>
              </div>

              <div className="auth-input-group">
                <label>Password</label>
                <div className="input-with-icon">
                  <Lock size={16} className="field-icon" />
                  <input
                    type="password"
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value)}
                    placeholder="Create a password"
                  />
                </div>
              </div>

              <div className="auth-input-group">
                <label>Confirm Password</label>
                <div className="input-with-icon">
                  <Lock size={16} className="field-icon" />
                  <input
                    type="password"
                    value={signupConfirmPassword}
                    onChange={(e) => setSignupConfirmPassword(e.target.value)}
                    placeholder="Repeat password"
                  />
                </div>
              </div>

              <div className="auth-form-actions">
                <button type="submit" className="auth-primary-btn">
                  <Sparkles size={14} />
                  <span>Create Account</span>
                </button>
                <button
                  type="button"
                  className="auth-link-btn"
                  onClick={() => setActiveTab('login')}
                >
                  <span>Already have an account? Sign In</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </motion.div>
    </div>
  );
};
