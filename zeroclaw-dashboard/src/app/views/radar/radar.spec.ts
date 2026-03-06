import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Radar } from './radar';

describe('Radar', () => {
  let component: Radar;
  let fixture: ComponentFixture<Radar>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Radar]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Radar);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
