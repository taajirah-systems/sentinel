import { TestBed } from '@angular/core/testing';

import { Zeroclaw } from './zeroclaw';

describe('Zeroclaw', () => {
  let service: Zeroclaw;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Zeroclaw);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
