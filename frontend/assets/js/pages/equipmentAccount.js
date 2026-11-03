/**
 * Equipment owner decisions and a renter's own requests.
 * Uses the existing booking and inquiry endpoints.
 */

const EquipmentAccount = {
  busy: false,

  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  mountOwner(card) {
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('equip.ownerNote');
    const add = document.createElement('a');
    add.className = 'btn btn-primary btn-sm';
    add.href = EquipmentAccountLogic.LISTING_FORM_PATH;
    add.textContent = this.text('equip.addListing');
    const status = document.createElement('p');
    status.id = 'equipment-owner-status';
    status.setAttribute('role', 'status');
    status.textContent = this.text('equip.loadingListings');
    const list = document.createElement('div');
    list.id = 'equipment-owner-list';
    card.append(note, add, status, list);
    this.loadOwner(status, list);
  },

  mountRenter(card) {
    const browse = document.createElement('a');
    browse.className = 'btn btn-outline';
    browse.href = '../equipment/equipment-list.html';
    browse.textContent = this.text('equip.browseListings');
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('equip.renterNote');
    const status = document.createElement('p');
    status.id = 'equipment-renter-status';
    status.setAttribute('role', 'status');
    status.textContent = this.text('equip.loadingRequests');
    const list = document.createElement('div');
    list.id = 'equipment-renter-list';
    card.append(browse, note, status, list);
    this.loadRenter(status, list);
  },

  async collect(path) {
    const rows = [];
    let endpoint = path;
    while (endpoint) {
      const page = await ApiClient.get(endpoint);
      if (Array.isArray(page)) return page;
      rows.push(...(page.results || []));
      if (!page.next || !page.next.startsWith(CONFIG.API_BASE_URL)) break;
      endpoint = page.next.slice(CONFIG.API_BASE_URL.length);
    }
    return rows;
  },

  async loadOwner(status, list) {
    try {
      const listings = (await this.collect(EquipmentAccountLogic.LISTINGS_PATH)).filter((item) => item.is_owner);
      list.replaceChildren();
      if (!listings.length) {
        status.textContent = this.text('equip.noListings');
        return;
      }
      let requests = 0;
      for (const listing of listings) {
        const bookings = await this.collect(EquipmentAccountLogic.listingBookingsPath(listing.id));
        const inquiries = await this.collect(EquipmentAccountLogic.listingInquiriesPath(listing.id));
        requests += bookings.length + inquiries.length;
        list.appendChild(this.listingBlock(listing, bookings, inquiries));
      }
      status.textContent = requests
        ? this.text('equip.requestCount', { count: requests })
        : this.text('equip.noActivity');
    } catch (error) {
      status.textContent = EquipmentDetailsLogic.errorText(error);
    }
  },

  async loadRenter(status, list) {
    try {
      const bookings = await this.collect(EquipmentAccountLogic.MY_BOOKINGS_PATH);
      list.replaceChildren();
      if (!bookings.length) {
        status.textContent = this.text('equip.noRequests');
        return;
      }
      status.textContent = this.text('equip.renterCount', { count: bookings.length });
      bookings.forEach((booking) => list.appendChild(this.renterRow(booking)));
    } catch (error) {
      status.textContent = EquipmentDetailsLogic.errorText(error);
    }
  },

  listingBlock(listing, bookings, inquiries) {
    const block = document.createElement('section');
    block.className = 'card';
    block.style.padding = '12px';
    block.style.marginBottom = '16px';
    const header = document.createElement('div');
    header.className = 'listing-card';
    header.style.marginBottom = '0';
    const media = document.createElement('div');
    media.className = 'listing-card-media';
    const image = document.createElement('img');
    image.src = typeof KaamdoImages !== 'undefined'
      ? KaamdoImages.equipmentPhoto(listing.photo_url)
      : '../../assets/images/placeholders/tractor-default.jpg';
    image.alt = listing.title || '';
    image.loading = 'lazy';
    media.appendChild(image);
    const body = document.createElement('div');
    body.className = 'listing-card-body';
    const title = document.createElement('h3');
    title.textContent = listing.title;
    const meta = document.createElement('p');
    meta.className = 'text-muted';
    const publicListing = listing.status === 'published'
      && (listing.fee_status === 'paid' || listing.fee_status === 'waived');
    meta.textContent = publicListing ? this.text('equip.publicListing') : this.text('equip.notPublic');
    body.append(title, meta);
    header.append(media, body);
    block.appendChild(header);
    if (!bookings.length && !inquiries.length) {
      const empty = document.createElement('p');
      empty.className = 'text-muted';
      empty.textContent = this.text('equip.noListingRequests');
      block.appendChild(empty);
      return block;
    }
    bookings.forEach((booking) => block.appendChild(this.bookingRow(booking)));
    inquiries.forEach((inquiry) => block.appendChild(this.inquiryRow(inquiry)));
    return block;
  },

  bookingRow(booking) {
    const row = document.createElement('article');
    const copy = document.createElement('p');
    copy.textContent = `Request ${booking.id}: ${booking.start_date} to ${booking.end_date}. Status: ${booking.status}. ${booking.note || ''}`;
    const actions = document.createElement('p');
    actions.setAttribute('role', 'status');
    row.append(copy, actions);
    this.buttons(actions, EquipmentAccountLogic.bookingActions(booking), (status) => {
      this.decide(EquipmentAccountLogic.bookingDecisionPath(booking.id), status, 'booking', actions, copy, booking);
    });
    return row;
  },

  inquiryRow(inquiry) {
    const row = document.createElement('article');
    const copy = document.createElement('p');
    const timing = inquiry.preferred_timing ? ` Timing: ${inquiry.preferred_timing}.` : '';
    copy.textContent = `Inquiry ${inquiry.id}: ${inquiry.requirement}.${timing} Phone: ${inquiry.contact_phone || ''}. Status: ${inquiry.status}.`;
    const actions = document.createElement('p');
    actions.setAttribute('role', 'status');
    row.append(copy, actions);
    this.buttons(actions, EquipmentAccountLogic.inquiryActions(inquiry), (status) => {
      this.decide(EquipmentAccountLogic.inquiryDecisionPath(inquiry.id), status, 'inquiry', actions, copy, inquiry);
    });
    return row;
  },

  renterRow(booking) {
    const row = document.createElement('article');
    const copy = document.createElement('p');
    copy.textContent = `Listing ${booking.listing}: ${booking.start_date} to ${booking.end_date}. Status: ${booking.status}.`;
    row.appendChild(copy);
    return row;
  },

  buttons(actions, names, onChoose) {
    actions.replaceChildren();
    names.forEach((name) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-outline btn-sm';
      button.style.marginRight = '8px';
      button.textContent = this.text(`equip.action.${name}`);
      button.addEventListener('click', () => onChoose(name));
      actions.appendChild(button);
    });
  },

  async decide(path, status, kind, actions, copy, record) {
    if (this.busy) return;
    this.busy = true;
    actions.textContent = this.text('form.saving');
    try {
      const data = await ApiClient.patch(path, EquipmentAccountLogic.decisionPayload(status));
      record.status = data.status;
      copy.textContent = copy.textContent.replace(/Status: [^.]+\./, `Status: ${data.status}.`);
      actions.textContent = EquipmentAccountLogic.decisionResult(data, kind).text;
    } catch (error) {
      actions.textContent = EquipmentDetailsLogic.errorText(error);
    } finally {
      this.busy = false;
    }
  },
};
