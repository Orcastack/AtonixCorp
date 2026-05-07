import React, { useState } from 'react';

const Achievements = () => {
  const [currentLevel] = useState(7);
  const [currentXP] = useState(3850);
  const [xpToNextLevel] = useState(5000);
  const [streak] = useState(23);

  const badges = [
    { id: 1, name: 'First Deposit', earned: true, date: '2025-11-01', xp: 100 },
    { id: 2, name: 'Budget Master', earned: true, date: '2025-11-15', xp: 250 },
    { id: 3, name: 'Savings Champion', earned: true, date: '2025-12-01', xp: 500 },
    { id: 4, name: '30-Day Streak', earned: false, xp: 300 },
    { id: 5, name: 'Investment Pioneer', earned: true, date: '2025-11-20', xp: 400 },
    { id: 6, name: 'AI Insights User', earned: true, date: '2025-12-10', xp: 150 },
    { id: 7, name: 'Security Expert', earned: true, date: '2025-12-05', xp: 300 },
    { id: 8, name: 'Portfolio Diversifier', earned: false, xp: 350 },
    { id: 9, name: 'Referral Master', earned: false, xp: 500 },
    { id: 10, name: 'Financial DNA Analyzed', earned: true, date: '2025-12-12', xp: 200 },
  ];

  const missions = [
    { id: 1, title: 'Complete your Financial DNA Profile', reward: '200 XP', progress: 100, completed: true },
    { id: 2, title: 'Make 5 budget-conscious transactions', reward: '150 XP', progress: 80, completed: false },
    { id: 3, title: 'Maintain 7-day financial streak', reward: '100 XP', progress: 100, completed: true },
    { id: 4, name: 'Refer 3 friends to Ledgora', reward: '500 XP', progress: 33, completed: false },
    { id: 5, title: 'Invest in 3 different vaults', reward: '300 XP', progress: 66, completed: false },
    { id: 6, title: 'Enable all security features', reward: '250 XP', progress: 100, completed: true },
  ];

  const journey = [
    {
      id: 1,
      title: 'Started Financial Journey',
      date: '2025-11-01',
      description: 'Created account and made first deposit',
      milestone: true
    },
    {
      id: 2,
      title: 'Set Up First Budget',
      date: '2025-11-05',
      description: 'Created budgets for 5 categories',
      },
    {
      id: 3,
      title: 'Achieved Savings Goal',
      date: '2025-11-15',
      description: 'Saved $5,000 milestone',
      milestone: true
    },
    {
      id: 4,
      title: 'First Investment',
      date: '2025-11-20',
      description: 'Invested in Treasury Vault',
      },
    {
      id: 5,
      title: 'Analyzed Financial DNA',
      date: '2025-12-12',
      description: 'Discovered your financial personality',
      },
    {
      id: 6,
      title: 'Level 7 Achieved',
      date: '2025-12-15',
      description: 'Reached Wealth Master tier',
      milestone: true
    },
  ];

  const reputationScore = {
    overall: 845,
    kyc: 'Verified Level 2',
    investmentScore: 72,
    referralScore: 15,
    trustBadges: ['Early Adopter', 'Verified User', 'Active Trader']
  };

  return (
    <div className="achievements-page">
      <div className="page-header">
        <h1>Achievements & Progress</h1>
        <p>Track your financial growth journey and earn rewards</p>
      </div>

      {/* Level & XP Progress */}
      <div className="level-card">
        <div className="level-info">
          <div className="level-badge">
            <span className="level-number">{currentLevel}</span>
            <span className="level-label">LEVEL</span>
          </div>
          <div className="level-details">
            <h2>Wealth Master</h2>
            <p>You've mastered the fundamentals of financial management</p>
            <div className="xp-bar">
              <div
                className="xp-fill"
                style={{ width: `${(currentXP / xpToNextLevel) * 100}%` }}
              ></div>
            </div>
            <span className="xp-text">{currentXP} / {xpToNextLevel} XP to Level {currentLevel + 1}</span>
          </div>
        </div>

        <div className="streak-display">
          <div className="streak-icon"></div>
          <div className="streak-info">
            <span className="streak-number">{streak}</span>
            <span className="streak-label">Day Streak</span>
          </div>
          <p className="streak-message">Keep going! Hit 30 days for a bonus badge!</p>
        </div>
      </div>

      {/* Achievements Grid */}
      <div className="section-header">
        <h2>Your Badges</h2>
        <p>{badges.filter(b => b.earned).length} of {badges.length} earned</p>
      </div>

      <div className="badges-grid">
        {badges.map(badge => (
          <div key={badge.id} className={`badge-card ${badge.earned ? 'earned' : 'locked'}`}>
            <div className="badge-icon">{badge.icon}</div>
            <h3>{badge.name}</h3>
            {badge.earned ? (
              <>
                <span className="badge-xp">+{badge.xp} XP</span>
                <span className="badge-date">Earned {badge.date}</span>
              </>
            ) : (
              <>
                <span className="badge-locked">Locked</span>
                <span className="badge-xp">{badge.xp} XP</span>
              </>
            )}
          </div>
        ))}
      </div>

      {/* Active Missions */}
      <div className="section-header">
        <h2>Active Missions</h2>
        <p>Complete missions to earn bonus XP and unlock achievements</p>
      </div>

      <div className="missions-list">
        {missions.map(mission => (
          <div key={mission.id} className={`mission-card ${mission.completed ? 'completed' : ''}`}>
            <div className="mission-icon">{mission.icon}</div>
            <div className="mission-info">
              <h3>{mission.title}</h3>
              <div className="mission-progress-bar">
                <div
                  className="mission-progress-fill"
                  style={{ width: `${mission.progress}%` }}
                ></div>
              </div>
              <span className="mission-progress-text">{mission.progress}% Complete</span>
            </div>
            <div className="mission-reward">
              <span className="reward-badge">{mission.reward}</span>
              {mission.completed && <span className="completed-check"></span>}
            </div>
          </div>
        ))}
      </div>

      {/* Financial Journey Timeline */}
      <div className="section-header">
        <h2>Your Financial Journey</h2>
        <p>A visual story of your financial milestones</p>
      </div>

      <div className="journey-timeline">
        {journey.map((event, index) => (
          <div key={event.id} className={`timeline-item ${event.milestone ? 'milestone' : ''}`}>
            <div className="timeline-marker">
              <span className="timeline-icon">{event.icon}</span>
            </div>
            <div className="timeline-content">
              <div className="timeline-date">{event.date}</div>
              <h3>{event.title}</h3>
              <p>{event.description}</p>
              {event.milestone && <span className="milestone-badge">Milestone </span>}
            </div>
          </div>
        ))}
      </div>

      {/* Reputation Score */}
      <div className="reputation-section">
        <h2>Reputation & Trust Score</h2>
        <div className="reputation-display">
          <div className="reputation-score-circle">
            <span className="rep-score">{reputationScore.overall}</span>
            <span className="rep-label">/1000</span>
          </div>
          <div className="reputation-details">
            <div className="rep-metric">
              <span className="rep-metric-label">KYC Status</span>
              <span className="rep-metric-value verified">{reputationScore.kyc}</span>
            </div>
            <div className="rep-metric">
              <span className="rep-metric-label">Investment Score</span>
              <span className="rep-metric-value">{reputationScore.investmentScore}/100</span>
            </div>
            <div className="rep-metric">
              <span className="rep-metric-label">Referral Score</span>
              <span className="rep-metric-value">{reputationScore.referralScore} users</span>
            </div>
          </div>
        </div>

        <div className="trust-badges">
          <h3>Trust Badges</h3>
          <div className="badges-row">
            {reputationScore.trustBadges.map((badge, index) => (
              <span key={index} className="trust-badge">{badge}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Achievements;
