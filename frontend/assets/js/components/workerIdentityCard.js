/**
 * Digital Worker ID card from a worker_identity or assigned_profile payload.
 * Ratings are omitted. Phone, documents, and coordinates are never shown.
 */

const WorkerIdentityCard = {
  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  optionalNumber(value) {
    if (value == null || value === '') return null;
    const number = Number(value);
    if (!Number.isFinite(number) || number < 0) return null;
    return number;
  },

  normalize(source) {
    if (!source || typeof source !== 'object') return null;
    const primary = source.worker_identity && typeof source.worker_identity === 'object'
      ? source.worker_identity
      : null;
    const extra = source.assigned_profile && typeof source.assigned_profile === 'object'
      ? source.assigned_profile
      : null;
    const raw = primary || extra || source;
    const name = String((primary && primary.display_name) || (extra && extra.display_name) || raw.display_name || '').trim();
    const workerId = String((primary && primary.worker_id) || raw.worker_id || '').trim();
    if (!name && !workerId) return null;
    const photo = String((primary && primary.photo_url) || raw.photo_url || '').trim();
    const skillsSource = Array.isArray(raw.skills) ? raw.skills : [];
    const profileId = primary && primary.profile_id != null
      ? primary.profile_id
      : (raw.profile_id != null ? raw.profile_id : (raw.id != null ? raw.id : null));
    return {
      worker_id: workerId,
      profile_id: profileId,
      display_name: name,
      photo_url: /^https?:\/\//i.test(photo) ? photo : '',
      main_category: String((primary && primary.main_category) || raw.main_category || '').trim(),
      skills: skillsSource.map((item) => String(item)),
      identity_verification: String((primary && primary.identity_verification) || raw.identity_verification || '').trim(),
      identity_verified: (primary ? primary.identity_verified : raw.identity_verified) === true,
      skill_verified: false,
      qualification_verified: false,
      experience_years: this.optionalNumber(primary ? primary.experience_years : raw.experience_years),
      completed_jobs: this.optionalNumber(primary ? primary.completed_jobs : raw.completed_jobs),
      district: String((primary && primary.district) || (extra && extra.district) || raw.district || '').trim(),
      locality: String((primary && primary.locality) || (extra && extra.locality) || raw.locality || '').trim(),
    };
  },

  initials(name) {
    if (typeof ProviderStatusLogic !== 'undefined') return ProviderStatusLogic.initials(name);
    const parts = String(name || '').trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return '';
    const last = parts.length > 1 ? parts[parts.length - 1].charAt(0) : '';
    return `${parts[0].charAt(0)}${last}`.toUpperCase();
  },

  render(source) {
    if (typeof document === 'undefined') return null;
    const card = this.normalize(source);
    if (!card) return null;
    const article = document.createElement('article');
    article.className = 'worker-identity-card';

    const photoWrap = document.createElement('div');
    photoWrap.className = 'worker-identity-photo';
    if (card.photo_url) {
      const img = document.createElement('img');
      img.src = card.photo_url;
      img.alt = card.display_name
        ? this.text('identity.photoAlt', { name: card.display_name })
        : this.text('identity.workerId');
      photoWrap.appendChild(img);
    } else {
      const initials = document.createElement('span');
      initials.className = 'worker-identity-initials';
      initials.setAttribute('aria-hidden', 'true');
      initials.textContent = this.initials(card.display_name || card.worker_id);
      photoWrap.appendChild(initials);
    }

    const body = document.createElement('div');
    body.className = 'worker-identity-body';
    const name = document.createElement('h3');
    name.textContent = card.display_name || this.text('identity.workerId');
    body.appendChild(name);

    if (card.worker_id) {
      const idLine = document.createElement('p');
      idLine.className = 'worker-identity-id';
      idLine.textContent = `${this.text('identity.workerId')} ${card.worker_id}`;
      body.appendChild(idLine);
    }

    const badge = document.createElement('p');
    const mark = document.createElement('span');
    mark.className = card.identity_verified ? 'identity-badge' : 'identity-badge is-pending';
    mark.textContent = card.identity_verified
      ? this.text('identity.verified')
      : this.text('identity.notVerified');
    badge.appendChild(mark);
    body.appendChild(badge);

    if (card.main_category) {
      const category = document.createElement('p');
      category.textContent = `${this.text('identity.category')}: ${card.main_category}`;
      body.appendChild(category);
    }
    if (card.skills.length) {
      const skills = document.createElement('p');
      skills.textContent = `${this.text('identity.skills')}: ${card.skills.join(', ')}`;
      body.appendChild(skills);
      const note = document.createElement('p');
      note.className = 'text-muted';
      note.textContent = this.text('identity.skillsNote');
      body.appendChild(note);
    }
    if (card.experience_years != null) {
      const experience = document.createElement('p');
      experience.textContent = this.text('identity.experience', { years: card.experience_years });
      body.appendChild(experience);
    }
    if (card.completed_jobs != null) {
      const completed = document.createElement('p');
      completed.textContent = this.text('identity.completed', { count: card.completed_jobs });
      body.appendChild(completed);
    }
    const place = [card.locality, card.district].filter(Boolean).join(', ');
    if (place) {
      const placeLine = document.createElement('p');
      placeLine.className = 'text-muted';
      placeLine.textContent = this.text('identity.place', { place });
      body.appendChild(placeLine);
    }

    article.append(photoWrap, body);
    return article;
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = WorkerIdentityCard;
}
