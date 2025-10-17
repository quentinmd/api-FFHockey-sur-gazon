import React, { useState } from 'react';
import axios from 'axios';
import '../styles/Newsletter.css';

export default function Newsletter() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState('idle'); // idle, loading, success, error
  const [message, setMessage] = useState('');
  const [isSubscribed, setIsSubscribed] = useState(false);

  const API_BASE = 'http://localhost:8000/api/v1';

  const handleSubscribe = async (e) => {
    e.preventDefault();

    if (!email) {
      setMessage('Veuillez entrer une adresse email');
      setStatus('error');
      return;
    }

    setStatus('loading');

    try {
      const response = await axios.post(`${API_BASE}/subscribe`, {
        email: email,
      });

      if (response.data.success) {
        setMessage(`✅ Abonné avec succès à ${email}`);
        setStatus('success');
        setEmail('');
        setIsSubscribed(true);

        // Réinitialiser après 5 secondes
        setTimeout(() => {
          setStatus('idle');
          setMessage('');
          setIsSubscribed(false);
        }, 5000);
      }
    } catch (error) {
      setMessage('❌ Erreur lors de l\'abonnement. Essayez à nouveau.');
      setStatus('error');

      // Réinitialiser après 5 secondes
      setTimeout(() => {
        setStatus('idle');
        setMessage('');
      }, 5000);
    }
  };

  const handleUnsubscribe = async () => {
    if (!email) {
      setMessage('Veuillez entrer une adresse email');
      setStatus('error');
      return;
    }

    setStatus('loading');

    try {
      const response = await axios.delete(`${API_BASE}/unsubscribe`, {
        data: { email: email },
      });

      if (response.data.success) {
        setMessage(`✅ Désinscrit avec succès: ${email}`);
        setStatus('success');
        setEmail('');
        setIsSubscribed(false);

        // Réinitialiser après 5 secondes
        setTimeout(() => {
          setStatus('idle');
          setMessage('');
        }, 5000);
      }
    } catch (error) {
      setMessage('❌ Erreur lors de la désinscription.');
      setStatus('error');

      // Réinitialiser après 5 secondes
      setTimeout(() => {
        setStatus('idle');
        setMessage('');
      }, 5000);
    }
  };

  return (
    <div className="newsletter-container">
      <div className="newsletter-card">
        <div className="newsletter-header">
          <h3>📧 Notifications par Email</h3>
          <p>Recevez un email à la fin de chaque match</p>
        </div>

        <form onSubmit={handleSubscribe} className="newsletter-form">
          <div className="form-group">
            <input
              type="email"
              placeholder="Votre adresse email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={status === 'loading'}
              className="email-input"
            />
          </div>

          <div className="form-actions">
            <button
              type="submit"
              disabled={status === 'loading'}
              className={`btn btn-subscribe ${status === 'loading' ? 'loading' : ''}`}
            >
              {status === 'loading' ? '⏳ En cours...' : '✉️ S\'abonner'}
            </button>

            <button
              type="button"
              onClick={handleUnsubscribe}
              disabled={status === 'loading' || !email}
              className="btn btn-unsubscribe"
            >
              Se désabonner
            </button>
          </div>
        </form>

        {message && (
          <div className={`message message-${status}`}>
            {message}
          </div>
        )}

        <div className="newsletter-info">
          <p className="info-text">
            💡 Vous recevrez un email HTML formaté avec tous les détails du match dès que celui-ci se termine.
          </p>
        </div>
      </div>
    </div>
  );
}
