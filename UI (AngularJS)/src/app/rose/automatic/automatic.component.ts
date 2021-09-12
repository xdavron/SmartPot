import { Time } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ResourceService } from 'src/app/services/resource.service';

@Component({
  selector: 'app-automatic',
  templateUrl: './automatic.component.html',
  styleUrls: ['./automatic.component.scss']
})
export class AutomaticComponent implements OnInit {

  public checkModel: any = {
    monday: false,
    tuesday: false,
    wednesday: false,
    thursday: false,
    friday: false,
    saturday: false,
    sunday: false
  };

  public lie: boolean = false;

  public dur?: number;
  public dur2?: number;
  public timeW = '08:00';
  public timeL = '08:30';
  public time2 = '20:00';
  public secondTime: boolean = false;
  public time3 = '20:30';
  public thirdTime: boolean = false;

  public checkModel2: any = {
    water: false,
    light: false
  };

  public activeAuto: boolean;

  private week = [
    {

    },
    {
    },
    {
    },
    {
    },
    {
    },
    {
    },
    {
    }
  ];

  private plantId = "";
  private isFeed: boolean = false;

  constructor(private router: Router, private  resourceService: ResourceService, private activeRoute: ActivatedRoute) {
    this.activeAuto = false;
  }

  ngOnInit(): void {
    this.plantId = this.router.url.split('/')[1].split(';')[0];

    this.activeRoute.queryParamMap.subscribe(paramMap => {
      this.activeAuto = paramMap.get("auto")==="true";
    })

    this.getSchedule();
    this.getPlantStatus();
  }

  private getPlantStatus() {
    this.resourceService.getPlantStatus(this.plantId).subscribe(
      (data) => {
        if (data.includes('feedback')) {
          this.isFeed = true;
        }
      },
      error => {
        console.log(error);
      }
    );
  }

  public setSchedule() {

    let time = (<HTMLInputElement>document.getElementById("inputTime")).value + ":00";
    let duration = parseInt((<HTMLInputElement>document.getElementById("inputDuration")).value);
    if (duration.toString() == "NaN") {
      duration = -1;
    }
    if (!this.dur) {
      this.dur = -1;
    }
    if (!this.dur2) {
      this.dur2 = -1;
    }

    for (const x in this.checkModel) {
      if (this.checkModel[x] === true) {
        switch (x) {
          case 'monday':
            if (!this.secondTime && !this.thirdTime) {
              this.week[0] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.secondTime && this.thirdTime) {
              this.week[0] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            } else if (this.secondTime) {
              this.week[0] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.thirdTime) {
              this.week[0] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            }
            break;

          case 'tuesday':
            if (!this.secondTime && !this.thirdTime) {
              this.week[1] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.secondTime && this.thirdTime) {
              this.week[1] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            } else if (this.secondTime) {
              this.week[1] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.thirdTime) {
              this.week[1] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            }
            break;

          case 'wednesday':
            if (!this.secondTime && !this.thirdTime) {
              this.week[2] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.secondTime && this.thirdTime) {
              this.week[2] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            } else if (this.secondTime) {
              this.week[2] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.thirdTime) {
              this.week[2] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            }
            break;

          case 'thursday':
            if (!this.secondTime && !this.thirdTime) {
              this.week[3] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.secondTime && this.thirdTime) {
              this.week[3] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            } else if (this.secondTime) {
              this.week[3] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.thirdTime) {
              this.week[3] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            }
            break;

          case 'friday':
            if (!this.secondTime && !this.thirdTime) {
              this.week[4] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.secondTime && this.thirdTime) {
              this.week[4] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            } else if (this.secondTime) {
              this.week[4] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.thirdTime) {
              this.week[4] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            }
            break;

          case 'saturday':
            if (!this.secondTime && !this.thirdTime) {
              this.week[5] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.secondTime && this.thirdTime) {
              this.week[5] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            } else if (this.secondTime) {
              this.week[5] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.thirdTime) {
              this.week[5] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            }
            break;

          case 'sunday':
            if (!this.secondTime && !this.thirdTime) {
              this.week[6] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.secondTime && this.thirdTime) {
              this.week[6] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            } else if (this.secondTime) {
              this.week[6] = {
                water: {
                  [this.timeW]: this.dur,
                  [this.time2]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2
                }
              }
            } else if (this.thirdTime) {
              this.week[6] = {
                water: {
                  [this.timeW]: this.dur
                },
                light: {
                  [this.timeL]: this.dur2,
                  [this.time3]: this.dur2
                }
              }
            }
            break;
        }
      }
    }

    setTimeout(() => {
      let plantJson = {
        [ this.plantId ]: {
          "type": "weekly",
          "schedData": this.week
        }
      }
      console.log(JSON.stringify(plantJson));


      this.resourceService.setPlantAutoSchedule(this.plantId, JSON.stringify(plantJson)).subscribe(
        (data) => {
          this.lie = false;
          console.log(data);


        },
        error => console.log(error)

      );


    }, 50);

  }

  private getSchedule() {
    this.resourceService.getAutomaticSchedule(this.plantId).subscribe(
      (data) => {
        this.lie = false;

        for (let i = 0; i < data.length; i++) {

          if (data[i].water || data[i].light) {
            let j = 0;
            for (var key in data[i].light) {
              if (j === 0) {
                this.dur2 = parseInt(data[i].light[key]);
                this.timeL = key.slice(0, 5);
                j++;
              } else if (j === 1) {
                this.time3 = key.slice(0, 5);
                this.addTimer2();
              }
            }
            j = 0;
            for (var key in data[i].water) {
              if (j === 0) {
                this.dur = parseInt(data[i].water[key]);
                this.timeW = key.slice(0, 5);
                j++;
              } else if (j === 1) {
                this.time2 = key.slice(0, 5);
                this.addTimer();
              }
            }
            this.checkModel2.water = data[i].water ? true : null;
            this.checkModel2.light = data[i].light ? true : null;
            switch (i) {
              case 0:
                this.checkModel.monday = true;
                break;
              case 1:
                this.checkModel.tuesday = true;
                break;
              case 2:
                this.checkModel.wednesday = true;
                break;
              case 3:
                this.checkModel.thursday = true;
                break;
              case 4:
                this.checkModel.friday = true;
                break;
              case 5:
                this.checkModel.saturday = true;
                break;
              case 6:
                this.checkModel.sunday = true;
                break;
            }
          }
        }
      },
      (error) => {
        if (error.status !== 200) {
          console.log(error)
        } else {
          this.lie = true;
        }
      }
    );
  }

  public changeStatus() {
    if (this.activeAuto) {
      this.resourceService.setPlantStatusAutoDisable(this.plantId).subscribe(
        (data) => {
          this.activeAuto = false
          document.getElementById('autoId')?.classList.remove('active')

          this.router.navigate(['.'],
          {
            relativeTo: this.activeRoute,
            queryParams: { auto: false },
            queryParamsHandling: 'merge'
          })
        },
        error => {
          console.log(error);
        }
      )
    } else {
      if (!this.isFeed) {
        this.resourceService.setPlantStatusAutoEnable(this.plantId).subscribe(
          (data) => {
            this.activeAuto = true
            document.getElementById('autoId')?.classList.add('active')

            this.router.navigate(['.'],
            {
              relativeTo: this.activeRoute,
              queryParams: { auto: true },
              queryParamsHandling: 'merge'
            })
          },
          error => {
            if (error.status === 500) {
              this.activeAuto = true
              document.getElementById('autoId')?.classList.add('active')

              this.router.navigate(['.'],
              {
                relativeTo: this.activeRoute,
                queryParams: { auto: true },
                queryParamsHandling: 'merge'
              })
            }
            console.log(error.status);
          }
        )
      } else {
        document.getElementById("errButton")?.click();
        (<HTMLInputElement>document.getElementById("customSwitch2")).checked = false;
      }
    }
  }

  addTimer() {
    this.secondTime = true;
  }

  removeSecondTimer() {
    this.secondTime = false;
  }

  addTimer2() {
    this.thirdTime = true;
  }

  removeSecondTimer2() {
    this.thirdTime = false;
  }
}
