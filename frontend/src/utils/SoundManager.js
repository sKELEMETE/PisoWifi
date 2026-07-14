/**
 * SoundManager — centralized singleton for all portal audio.
 *
 * Design contract:
 *  - One Audio object per sound key, created once at preload().
 *  - Only one sound plays at a time (currentSound tracking).
 *  - Audio context is unlocked on first user interaction.
 *  - Console logging is compile-time stripped in production (import.meta.env.DEV guard).
 */

const IS_DEV = (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.DEV) || false;

function log(...args) {
    if (IS_DEV) console.log('[SoundManager]', ...args);
}

class SoundManager {
    constructor() {
        log('Initializing...');
        this.sounds = {};
        this.currentSound = null;
        this.unlocked = false;

        this.files = {
            explosion: '/api/sfx/explosion.mp3',
            nukeAlarm: '/api/sfx/nuke-alarm.mp3',
            chickenScreaming: '/api/sfx/chicken-screaming.mp3',
            success: '/api/sfx/success.mp3'
        };

        this._handleVisibilityChange = this._handleVisibilityChange.bind(this);
        this._unlockAudio = this._unlockAudio.bind(this);

        if (typeof document !== 'undefined') {
            document.addEventListener('visibilitychange', this._handleVisibilityChange);
            document.addEventListener('click', this._unlockAudio, { once: true });
            document.addEventListener('touchstart', this._unlockAudio, { once: true });
            document.addEventListener('keydown', this._unlockAudio, { once: true });
        }
    }

    _handleVisibilityChange() {
        if (document.hidden) {
            this.stopAll();
        }
    }

    _unlockAudio() {
        if (this.unlocked) return;
        this.unlocked = true;

        Object.entries(this.sounds).forEach(([key, audio]) => {
            if (!audio) return;
            const originalVolume = audio.volume;
            audio.volume = 0;
            const playPromise = audio.play();
            if (playPromise !== undefined) {
                playPromise.then(() => {
                    if (this.currentSound !== audio) {
                        audio.pause();
                        audio.currentTime = 0;
                    }
                    audio.volume = originalVolume;
                }).catch(() => {
                    audio.volume = originalVolume;
                });
            } else {
                audio.volume = originalVolume;
            }
        });
    }

    preload() {
        if (Object.keys(this.sounds).length > 0) return;

        for (const [key, path] of Object.entries(this.files)) {
            const audio = new Audio(path);
            audio.volume = 1;
            audio.preload = 'auto';
            if (key === 'nukeAlarm') {
                audio.loop = true;
            }
            audio.onerror = (e) => {
                if (IS_DEV) console.error(`[SoundManager] Audio error [${key}]:`, e, audio.error);
            };
            this.sounds[key] = audio;
        }
    }

    _play(key) {
        if (!this.sounds[key]) return;

        if (this.currentSound && this.currentSound !== this.sounds[key]) {
            this.currentSound.pause();
            this.currentSound.currentTime = 0;
            if (this.currentSound === this.sounds['chickenScreaming']) {
                this.sounds['chickenScreaming'].onended = null;
            }
            if (this.currentSound === this.sounds['explosion']) {
                this.sounds['explosion'].onended = null;
            }
        }

        this.currentSound = this.sounds[key];
        this.currentSound.currentTime = 0;
        this.currentSound.volume = 1;
        const playPromise = this.currentSound.play();
        if (playPromise !== undefined) {
            playPromise.catch(e => {
                if (IS_DEV) console.error(`[SoundManager] play-fail [${key}]:`, e);
            });
        }
    }

    playExplosion() {
        this._play('explosion');
    }

    playSuccess() {
        this._play('success');
    }

    playExplosionThenAlarm() {
        if (!this.sounds['explosion'] || !this.sounds['nukeAlarm']) return;

        this.stopAll();
        this.currentSound = this.sounds['explosion'];
        this.currentSound.currentTime = 0;
        this.currentSound.volume = 1;

        this.currentSound.onended = () => {
            this.sounds['explosion'].onended = null;
            this.startCountdownAlarm();
        };

        const playPromise = this.currentSound.play();
        if (playPromise !== undefined) {
            playPromise.catch(e => {
                if (IS_DEV) console.error('[SoundManager] playExplosionThenAlarm failed:', e);
            });
        }
    }

    startCountdownAlarm() {
        this._play('nukeAlarm');
    }

    stopCountdownAlarm() {
        if (this.currentSound === this.sounds['explosion']) {
            this.sounds['explosion'].onended = null;
        }
        if (this.currentSound === this.sounds['nukeAlarm']) {
            this.currentSound.pause();
            this.currentSound.currentTime = 0;
            this.currentSound = null;
        }
    }

    playSuccessSequence() {
        if (!this.sounds['chickenScreaming'] || !this.sounds['success']) return;

        this.stopAll();

        this.currentSound = this.sounds['chickenScreaming'];
        this.currentSound.currentTime = 0;
        this.currentSound.volume = 1;

        this.currentSound.onended = () => {
            this.sounds['chickenScreaming'].onended = null;
            this.currentSound = this.sounds['success'];
            this.currentSound.currentTime = 0;
            this.currentSound.volume = 1;
            const p = this.currentSound.play();
            if (p !== undefined) {
                p.catch(e => {
                    if (IS_DEV) console.error('[SoundManager] success play failed:', e);
                });
            }
        };

        const playPromise = this.currentSound.play();
        if (playPromise !== undefined) {
            playPromise.catch(e => {
                if (IS_DEV) console.error('[SoundManager] chicken play failed:', e);
            });
        }
    }

    stopAll() {
        if (this.currentSound) {
            this.currentSound.pause();
            this.currentSound.currentTime = 0;
            if (this.currentSound === this.sounds['chickenScreaming']) {
                this.sounds['chickenScreaming'].onended = null;
            }
            if (this.currentSound === this.sounds['explosion']) {
                this.sounds['explosion'].onended = null;
            }
            this.currentSound = null;
        }
    }
}

const soundManager = new SoundManager();
export default soundManager;
